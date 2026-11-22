import sys
import tempfile

sys.path.insert(0, "backend")

SENTENCES = [
    ("java", "Spring Boot mein REST controller kaise banate hain"),
    ("java", "JPA repository se database query likho"),
    ("java", "Java mein HashMap aur TreeMap ka farak"),
    ("java", "Maven pom.xml mein dependency add karo"),
    ("java", "JVM garbage collector memory saaf karta hai"),
    ("python", "FastAPI mein async route banao"),
    ("python", "Python list comprehension se loop chhota karo"),
    ("python", "pip install se package daalo"),
    ("python", "Pandas DataFrame mein CSV padho"),
    ("python", "virtualenv se project ka alag environment banao"),
    ("devops", "Docker image banane ke liye Dockerfile likho"),
    ("devops", "docker compose se database aur app ek saath chalao"),
    ("devops", "GitHub Actions har push pe tests chalata hai"),
    ("devops", "Kubernetes pod crash ho to logs dekho"),
    ("devops", "Nginx reverse proxy port 80 pe sunta hai"),
    ("food", "Paneer butter masala ke liye makhan aur tamatar chahiye"),
    ("food", "Chai mein adrak daalo to swaad badhta hai"),
    ("food", "Biryani dum pe pakao"),
    ("food", "Dosa ka batter raat bhar bhigo ke rakho"),
    ("food", "Samosa mein aloo aur matar bharo"),
]


def show(title: str, result: dict) -> None:
    print(f"\n=== {title} ===")
    for doc, meta, dist in zip(
        result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
    ):
        print(f"distance {dist:.3f}  score {1 - dist:.3f}  [{meta['topic']:6}] {doc}")


def main() -> None:
    import chromadb
    from app.ingestion import embedder
    from chromadb.config import Settings

    print("Loading embedding model...")
    vectors = embedder.embed([text for _, text in SENTENCES], kind="passage")

    with tempfile.TemporaryDirectory() as path:
        client = chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))
        col = client.get_or_create_collection(
            "day06_practice", metadata={"hnsw:space": "cosine"}, embedding_function=None
        )
        col.add(
            ids=[f"s{i}" for i in range(len(SENTENCES))],
            embeddings=vectors,
            documents=[text for _, text in SENTENCES],
            metadatas=[{"topic": topic} for topic, _ in SENTENCES],
        )
        print(f"Stored {col.count()} sentences in collection '{col.name}'")

        question = "database se data kaise nikaalein"
        q = embedder.embed_query(question)
        show(f"1. Top 4 for '{question}'", col.query(query_embeddings=[q], n_results=4))
        show(
            "2. Same question, only topic=java",
            col.query(query_embeddings=[q], n_results=4, where={"topic": "java"}),
        )
        show(
            "3. 'kuch khaane ka batao', only topic=food",
            col.query(
                query_embeddings=[embedder.embed_query("kuch khaane ka batao")],
                n_results=3,
                where={"topic": "food"},
            ),
        )
        print("\nDistance = 1 - cosine. Chhota distance = zyada milta-julta.")


if __name__ == "__main__":
    main()
