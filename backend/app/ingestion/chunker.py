from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Chunk:
    position: int
    start: float
    end: float
    text: str
    word_count: int
    first_segment: int
    last_segment: int


@dataclass(frozen=True)
class Piece:
    segment: int
    start: float
    end: float
    words: tuple[str, ...]


def check_sizes(max_words: int, overlap_words: int) -> None:
    if max_words < 1:
        raise ValueError("max_words must be at least 1")
    if not 0 <= overlap_words < max_words:
        raise ValueError("overlap_words must be between 0 and max_words - 1")


def to_pieces(segments: Sequence[Mapping[str, Any]], max_words: int) -> list[Piece]:
    pieces = []
    for i, seg in enumerate(segments):
        words = str(seg["text"]).split()
        if not words:
            continue
        start, end = float(seg["start"]), float(seg["end"])
        if len(words) <= max_words:
            pieces.append(Piece(i, start, end, tuple(words)))
            continue
        step = (end - start) / len(words)
        for j in range(0, len(words), max_words):
            part = words[j : j + max_words]
            pieces.append(Piece(i, start + j * step, start + (j + len(part)) * step, tuple(part)))
    return pieces


def make_chunk(position: int, group: list[Piece]) -> Chunk:
    words = [w for p in group for w in p.words]
    return Chunk(
        position=position,
        start=group[0].start,
        end=group[-1].end,
        text=" ".join(words),
        word_count=len(words),
        first_segment=group[0].segment,
        last_segment=group[-1].segment,
    )


def chunk_segments(
    segments: Sequence[Mapping[str, Any]], max_words: int = 300, overlap_words: int = 50
) -> list[Chunk]:
    check_sizes(max_words, overlap_words)
    pieces = to_pieces(segments, max_words)
    chunks: list[Chunk] = []
    i = 0
    while i < len(pieces):
        j, count = i, 0
        while j < len(pieces) and count + len(pieces[j].words) <= max_words:
            count += len(pieces[j].words)
            j += 1
        chunks.append(make_chunk(len(chunks), pieces[i:j]))
        if j >= len(pieces):
            break
        back, kept = j, 0
        while back - 1 > i and kept + len(pieces[back - 1].words) <= overlap_words:
            back -= 1
            kept += len(pieces[back].words)
        i = back
    return chunks


def chunk_words(text: str, max_words: int = 300, overlap_words: int = 50) -> list[str]:
    check_sizes(max_words, overlap_words)
    words = text.split()
    if not words:
        return []
    step = max_words - overlap_words
    last = max(len(words) - overlap_words, 1)
    return [" ".join(words[i : i + max_words]) for i in range(0, last, step)]


def shared_segments(a: Chunk, b: Chunk) -> int:
    return max(0, a.last_segment - b.first_segment + 1)


def stats(chunks: Sequence[Chunk]) -> dict[str, float]:
    if not chunks:
        return {"count": 0, "avg_words": 0, "min_words": 0, "max_words": 0}
    counts = [c.word_count for c in chunks]
    return {
        "count": len(chunks),
        "avg_words": round(sum(counts) / len(counts), 1),
        "min_words": min(counts),
        "max_words": max(counts),
    }
