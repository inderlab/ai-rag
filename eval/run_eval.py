import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.config import settings
from app.ingestion import embedder, youtube
from app.ingestion.chunker import Chunk, chunk_segments
from app.llm.factory import get_llm
from app.services import rag
from app.vectorstore.chroma_store import Hit

HERE = Path(__file__).resolve().parent
ANSWER_SLACK = 30


@dataclass
class Question:
    id: int
    question: str
    lang: str
    start: float
    end: float


def overlaps(chunk_start: float, chunk_end: float, q: Question) -> bool:
    return chunk_start <= q.end and chunk_end >= q.start


def load_segments(youtube_id: str, source: str) -> list[dict]:
    if source == "db":
        from app import db
        from app.models import TranscriptSegment, Video
        from sqlalchemy import select

        with db.SessionLocal() as session:
            video = session.scalar(select(Video).where(Video.youtube_id == youtube_id))
            if video is not None:
                rows = session.scalars(
                    select(TranscriptSegment)
                    .where(TranscriptSegment.video_id == video.id)
                    .order_by(TranscriptSegment.position)
                )
                segments = [{"text": r.text, "start": r.start, "end": r.end} for r in rows]
                if segments:
                    return segments
        print("Video not in the database, fetching captions from YouTube...")
    return youtube.fetch_captions(youtube_id).segments


def rank(q_vec: list[float], vectors: list[list[float]]) -> list[int]:
    scores = [sum(a * b for a, b in zip(q_vec, v, strict=True)) for v in vectors]
    return sorted(range(len(vectors)), key=lambda i: scores[i], reverse=True)


def fuse(orders: list[list[int]], c: int = 60) -> list[int]:
    scores: dict[int, float] = {}
    for order in orders:
        for n, i in enumerate(order, 1):
            scores[i] = scores.get(i, 0.0) + 1 / (c + n)
    return sorted(scores, key=lambda i: scores[i], reverse=True)


def retrieval_eval(
    segments: list[dict],
    questions: list[Question],
    size: int,
    overlap: int,
    ks: list[int],
    extra_queries: list[str] | None = None,
) -> dict:
    chunks = chunk_segments(segments, size, overlap)
    start = time.perf_counter()
    vectors = embedder.embed([c.text for c in chunks], kind="passage")
    index_ms = int((time.perf_counter() - start) * 1000)
    q_vectors = embedder.embed([q.question for q in questions], kind="query")
    x_vectors = embedder.embed(extra_queries, kind="query") if extra_queries else None
    top = max(ks)
    hits = {k: 0 for k in ks}
    reciprocal = 0.0
    misses = []
    for n_q, (q, q_vec) in enumerate(zip(questions, q_vectors, strict=True)):
        order = rank(q_vec, vectors)
        if x_vectors is not None:
            order = fuse([order, rank(x_vectors[n_q], vectors)])
        order = order[:top]
        first = next(
            (n for n, i in enumerate(order, 1) if overlaps(chunks[i].start, chunks[i].end, q)),
            None,
        )
        for k in ks:
            hits[k] += first is not None and first <= k
        reciprocal += 1 / first if first else 0
        if first is None:
            misses.append(q.id)
    n = len(questions)
    return {
        "chunk_words": size,
        "overlap_words": overlap,
        "chunks": len(chunks),
        "avg_words": round(sum(c.word_count for c in chunks) / max(len(chunks), 1), 1),
        "hit_rate": {f"@{k}": round(hits[k] / n, 3) for k in ks},
        "mrr": round(reciprocal / n, 3),
        "index_ms": index_ms,
        "misses": misses,
    }


def answer_eval(
    segments: list[dict], questions: list[Question], provider: str, k: int, title: str
) -> dict:
    llm = get_llm(provider)
    size, overlap = settings.CHUNK_MAX_WORDS, settings.CHUNK_OVERLAP_WORDS
    chunks: list[Chunk] = chunk_segments(segments, size, overlap)
    vectors = embedder.embed([c.text for c in chunks], kind="passage")
    rows = []
    for q in questions:
        order = rank(embedder.embed_query(q.question), vectors)[:k]
        hits = [
            Hit(0, chunks[i].position, chunks[i].start, chunks[i].end, chunks[i].text, 0.0, title)
            for i in order
        ]
        start = time.perf_counter()
        answer = rag.generate(llm, q.question, hits)
        latency = int((time.perf_counter() - start) * 1000)
        cited = [rag.to_seconds(ts) for ts in answer.citations]
        right = any(
            any(abs(h.start - s) <= 1 and overlaps(h.start, h.end, q) for h in hits)
            or q.start - ANSWER_SLACK <= s <= q.end + ANSWER_SLACK
            for s in cited
        )
        rows.append(
            {
                "id": q.id,
                "found": answer.found,
                "citations": answer.citations,
                "right_citation": right,
                "latency_ms": latency,
                "input_tokens": answer.input_tokens,
                "output_tokens": answer.output_tokens,
                "answer": answer.text,
            }
        )
        mark = "ok " if right else "MISS"
        print(f"  {mark} Q{q.id:02d} found={answer.found} cites={answer.citations} {latency} ms")
    n = len(rows)
    return {
        "provider": llm.name,
        "model": llm.model,
        "chunk_words": size,
        "k": k,
        "found_rate": round(sum(r["found"] for r in rows) / n, 3),
        "right_citation_rate": round(sum(r["right_citation"] for r in rows) / n, 3),
        "avg_latency_ms": int(sum(r["latency_ms"] for r in rows) / n),
        "input_tokens": sum(r["input_tokens"] for r in rows),
        "output_tokens": sum(r["output_tokens"] for r in rows),
        "rows": rows,
    }


def rewrite_eval(
    segments: list[dict], questions: list[Question], provider: str, ks: list[int]
) -> dict:
    from app.agents.router import route

    llm = get_llm(provider)
    rewritten = []
    for q in questions:
        query = route(llm, {"question": q.question, "video_id": 1})["search_query"]
        rewritten.append(Question(q.id, query, q.lang, q.start, q.end))
        print(f"  Q{q.id:02d} {q.question!r} -> {query!r}")
    size, overlap = settings.CHUNK_MAX_WORDS, settings.CHUNK_OVERLAP_WORDS
    out: dict = {"queries": {q.id: q.question for q in rewritten}}
    for mode in ("original", "rewritten", "both"):
        out[mode] = {}
        for lang in ["all", *sorted({q.lang for q in questions})]:
            idx = [i for i, q in enumerate(questions) if lang in ("all", q.lang)]
            base = (
                [questions[i] for i in idx] if mode != "rewritten" else [rewritten[i] for i in idx]
            )
            extra = [rewritten[i].question for i in idx] if mode == "both" else None
            r = retrieval_eval(segments, base, size, overlap, ks, extra)
            out[mode][lang] = {"questions": len(idx), "hit_rate": r["hit_rate"], "mrr": r["mrr"]}
    print(f"\nQuery modes at {size} words:")
    print("| Mode | Lang | Questions | " + " | ".join(f"Hit@{k}" for k in ks) + " | MRR |")
    print("|" + "---|" * (len(ks) + 4))
    for mode in ("original", "rewritten", "both"):
        for lang, r in out[mode].items():
            cells = " | ".join(f"{r['hit_rate'][f'@{k}']:.0%}" for k in ks)
            print(f"| {mode} | {lang} | {r['questions']} | {cells} | {r['mrr']:.2f} |")
    return out


def table(results: list[dict], ks: list[int]) -> str:
    head = "| Chunk words | Overlap | Chunks | " + " | ".join(f"Hit@{k}" for k in ks)
    lines = [head + " | MRR | Index ms |", "|" + "---|" * (len(ks) + 5)]
    for r in results:
        cells = " | ".join(f"{r['hit_rate'][f'@{k}']:.0%}" for k in ks)
        lines.append(
            f"| {r['chunk_words']} | {r['overlap_words']} | {r['chunks']} | {cells} "
            f"| {r['mrr']:.2f} | {r['index_ms']} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="VidMind retrieval and answer eval")
    parser.add_argument("--questions", default=str(HERE / "questions.json"))
    parser.add_argument("--sizes", default="150,300,600")
    parser.add_argument("--overlap", type=float, default=1 / 6)
    parser.add_argument("--k", default="1,3,6")
    parser.add_argument("--source", choices=["db", "youtube"], default="db")
    parser.add_argument("--provider", choices=["openai", "claude"], default=None)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--rewrite", action="store_true")
    args = parser.parse_args()

    spec = json.loads(Path(args.questions).read_text())
    questions = [
        Question(**{k: q[k] for k in ("id", "question", "lang", "start", "end")})
        for q in spec["questions"]
    ]
    if args.limit:
        questions = questions[: args.limit]
    ks = [int(k) for k in args.k.split(",")]
    sizes = [int(s) for s in args.sizes.split(",")]
    video = spec["video"]

    segments = load_segments(video["youtube_id"], args.source)
    words = sum(len(s["text"].split()) for s in segments)
    print(f"Video {video['youtube_id']}: {len(segments)} segments, {words} words")
    embedder.get_model()
    print(f"Embedding model: {embedder.model_name()}, questions: {len(questions)}\n")

    results = []
    for size in sizes:
        overlap = math.floor(size * args.overlap)
        r = retrieval_eval(segments, questions, size, overlap, ks)
        results.append(r)
        print(f"size {size}: hit {r['hit_rate']} mrr {r['mrr']} misses {r['misses']}")
    print("\n" + table(results, ks))

    by_lang = {}
    best = max(results, key=lambda r: (r["hit_rate"][f"@{max(ks)}"], r["mrr"]))
    report = {
        "date": datetime.now(UTC).isoformat(timespec="seconds"),
        "video": video,
        "embedding_model": embedder.model_name(),
        "questions": len(questions),
        "retrieval": results,
        "best_chunk_words": best["chunk_words"],
        "by_lang": by_lang,
    }
    for lang in sorted({q.lang for q in questions}):
        subset = [q for q in questions if q.lang == lang]
        r = retrieval_eval(
            segments, subset, settings.CHUNK_MAX_WORDS, settings.CHUNK_OVERLAP_WORDS, ks
        )
        by_lang[lang] = {"questions": len(subset), "hit_rate": r["hit_rate"], "mrr": r["mrr"]}
    print(f"\nBy language at {settings.CHUNK_MAX_WORDS} words: {by_lang}")

    if args.rewrite:
        report["rewrite"] = rewrite_eval(segments, questions, args.provider or "claude", ks)

    if args.provider:
        print(f"\nAnswer eval with {args.provider} (chunk {settings.CHUNK_MAX_WORDS}, k=6):")
        report["answers"] = answer_eval(segments, questions, args.provider, 6, video["title"])
        a = report["answers"]
        print(
            f"found {a['found_rate']:.0%}, right citation {a['right_citation_rate']:.0%}, "
            f"avg {a['avg_latency_ms']} ms, tokens {a['input_tokens']}+{a['output_tokens']}"
        )

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out = HERE / "results" / f"{stamp}.json"
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nSaved {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
