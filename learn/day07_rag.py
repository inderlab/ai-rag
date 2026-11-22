import sys

import httpx

API = "http://127.0.0.1:8000/api"

QUESTIONS = [
    "What is inside the model files, and how big are they?",
    "Pretraining ke liye kitna data aur GPU lagta hai?",
    "What is a jailbreak? Give one example from the talk.",
    "Who won the cricket world cup in 2011?",
]


def wrap(text: str, width: int = 90) -> str:
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    return "\n    ".join([*lines, line])


def main(video_id: int, api: str) -> None:
    with httpx.Client(base_url=api, timeout=120) as client:
        video = client.get(f"/videos/{video_id}").json()
        print(f"Video: {video['title']} ({video['chunk_count']} chunks)\n")

        first = QUESTIONS[0]
        compare = client.post("/chat/compare", json={"question": first, "video_id": video_id})
        if compare.status_code != 200:
            sys.exit(f"compare failed: {compare.status_code} {compare.text}")
        data = compare.json()
        print(f"=== 1. Without RAG vs with RAG: {first} ===")
        print(f"WITHOUT RAG:\n    {wrap(data['without_rag']['answer'])}")
        print(f"WITH RAG:\n    {wrap(data['with_rag']['answer'])}\n")

        print("=== 2. RAG answers with timestamps ===")
        for q in QUESTIONS:
            resp = client.post("/chat", json={"question": q, "video_id": video_id})
            if resp.status_code != 200:
                print(f"Q: {q}\n   failed: {resp.status_code} {resp.text}\n")
                continue
            r = resp.json()
            cites = ", ".join(c["timestamp"] for c in r["citations"]) or "-"
            print(f"Q: {q}")
            print(f"A: {wrap(r['answer'])}")
            print(f"   found={r['found']} citations={cites} tokens={r['input_tokens']}"
                  f"+{r['output_tokens']} retrieval={r['retrieval_ms']}ms llm={r['llm_ms']}ms\n")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1, sys.argv[2] if len(sys.argv) > 2 else API)
