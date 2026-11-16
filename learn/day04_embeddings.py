import sys
import time

sys.path.insert(0, "backend")

QUERY = "database kaise connect karein"

PASSAGES = [
    "application.properties mein datasource URL set karo",
    "aaj mausam bahut achha hai",
    "डेटाबेस कनेक्शन के लिए URL सेट करें",
    "How to configure the database connection string",
    "cricket match kal shaam 7 baje hai",
]

MY_SENTENCES = [
    "",
]


def bar(score: float, low: float, high: float) -> str:
    width = 30
    filled = int((score - low) / (high - low or 1) * width)
    return "█" * filled + "·" * (width - filled)


def main() -> None:
    from app.ingestion import embedder

    print("Loading model (first time downloads ~470 MB)...")
    start = time.perf_counter()
    model = embedder.get_model()
    print(
        f"{model.name} | {model.dimension} numbers per text | {time.perf_counter() - start:.1f}s\n"
    )

    vector = embedder.embed_query(QUERY)
    print(f"=== 1. '{QUERY}' as numbers ===")
    print([round(x, 3) for x in vector[:8]], f"... ({len(vector)} total)\n")

    passages = PASSAGES + [s for s in MY_SENTENCES if s.strip()]
    ranked = embedder.rank(QUERY, passages)
    low, high = ranked[-1][1], ranked[0][1]
    print("=== 2. Which passage means the same? ===")
    for i, score in ranked:
        print(f"{score:.3f} {bar(score, low, high)} {passages[i]}")

    print("\n=== 3. Same model rule ===")
    q = embedder.embed_query("hello")
    p = embedder.embed(["hello"], kind="passage")[0]
    print(f"'query: hello' vs 'passage: hello' = {embedder.cosine(q, p):.3f}")
    print(
        "Prefix changes the vector a little. Always embed questions as query, data as passage."
    )


if __name__ == "__main__":
    main()
