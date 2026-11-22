import json
import sys

import httpx

sys.path.insert(0, "backend")

API = "http://127.0.0.1:8000/api"


def verifier_demo() -> None:
    from app.agents import verifier
    from app.vectorstore.chroma_store import Hit

    hits = [
        Hit(2, 3, 221.0, 295.0, "about 10 terabytes of text ... 6,000 GPUs for 12 days", 0.88),
        Hit(2, 7, 2778.0, 2848.0, "act as my deceased grandmother ... napalm", 0.86),
    ]
    answers = {
        "good": "Pretraining uses ~10 TB of text and 6,000 GPUs [03:41].",
        "wrong time": "Pretraining uses ~10 TB of text [12:00] and 6,000 GPUs [03:41].",
        "no citation": "Pretraining uses ~10 TB of text and 6,000 GPUs.",
    }
    print("=== 1. Verifier on hand-made answers ===")
    for name, text in answers.items():
        from app.services.rag import find_citations

        cites = find_citations(text)
        first = verifier.verify({"answer": text, "citations": cites, "chunks": hits, "retries": 0})
        print(f"\n[{name}] {text}")
        print(f"  first check -> {first['steps'][0]}  notes={first['verify_notes']}")
        if first["steps"][0] == "verifier:retry":
            last = verifier.verify(
                {"answer": text, "citations": cites, "chunks": hits, "retries": 1}
            )
            print(f"  after retry still bad -> {last['steps'][0]}, cleaned: {last['answer']}")


def stream_demo(video_id: int, api: str) -> None:
    print("\n=== 2. Live multi-agent stream ===")
    body = {"question": "Pretraining ke liye kitna data aur GPU lagta hai?", "video_id": video_id}
    with httpx.stream("POST", f"{api}/chat/stream", json=body, timeout=180) as r:
        for line in r.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event["type"] == "token":
                print(event["text"], end="", flush=True)
            elif event["type"] == "step":
                print(f"\n  -> {event['node']} {event['steps']}", flush=True)
            elif event["type"] == "retry":
                print(f"\n  !! verifier asked for retry: {event['notes']}")
            elif event["type"] == "done":
                res = event["result"]
                print(f"\n  done: verified={res['verified']} citations="
                      f"{[c['timestamp'] for c in res['citations']]} {res['latency_ms']} ms")
            elif event["type"] == "error":
                print(f"\n  error: {event['detail']}")


def intents_demo(video_id: int, api: str) -> None:
    print("\n=== 3. One question per agent ===")
    questions = [
        ("Is video ka summary do", video_id),
        ("3 MCQ banao is video se", video_id),
        ("Kaunsi video prompt injection samjhati hai?", None),
    ]
    with httpx.Client(base_url=api, timeout=180) as client:
        for q, vid in questions:
            r = client.post("/chat", json={"question": q, "video_id": vid}).json()
            print(f"\nQ: {q}\n  steps={r['steps']} verified={r['verified']} {r['latency_ms']} ms")
            print("  " + r["answer"][:300].replace("\n", "\n  "))


if __name__ == "__main__":
    verifier_demo()
    if len(sys.argv) > 1:
        vid = int(sys.argv[1])
        base = sys.argv[2] if len(sys.argv) > 2 else API
        stream_demo(vid, base)
        intents_demo(vid, base)
