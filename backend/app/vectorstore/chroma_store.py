import threading
from collections.abc import Sequence
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.config import settings
from app.ingestion import embedder
from app.ingestion.chunker import Chunk


@dataclass(frozen=True)
class Hit:
    video_id: int
    position: int
    start: float
    end: float
    text: str
    score: float
    title: str = ""


class ModelMismatchError(RuntimeError):
    pass


class ChromaStore:
    def __init__(self, path: str, collection: str = "vidmind_chunks"):
        import chromadb
        from chromadb.config import Settings

        self.path = path
        self.client = chromadb.PersistentClient(
            path=path, settings=Settings(anonymized_telemetry=False)
        )
        self.name = collection
        self.collection = self.client.get_or_create_collection(
            collection,
            metadata={"hnsw:space": "cosine", "embedding_model": embedder.model_name()},
            embedding_function=None,
        )
        stored = (self.collection.metadata or {}).get("embedding_model")
        current = embedder.model_name()
        if stored and stored != current:
            raise ModelMismatchError(
                f"Collection '{collection}' was built with '{stored}' but the app uses "
                f"'{current}'. Re-index or change CHROMA_COLLECTION."
            )

    def add_chunks(self, video_id: int, chunks: Sequence[Chunk], title: str = "") -> int:
        self.delete_video(video_id)
        if not chunks:
            return 0
        vectors = embedder.embed([c.text for c in chunks], kind="passage")
        self.collection.upsert(
            ids=[f"{video_id}:{c.position}" for c in chunks],
            embeddings=vectors,
            documents=[c.text for c in chunks],
            metadatas=[
                {
                    "video_id": video_id,
                    "position": c.position,
                    "start": c.start,
                    "end": c.end,
                    "first_segment": c.first_segment,
                    "last_segment": c.last_segment,
                    "title": title,
                }
                for c in chunks
            ],
        )
        return len(chunks)

    def search(self, question: str, video_id: int | None = None, k: int = 6) -> list[Hit]:
        total = self.count(video_id)
        if total == 0:
            return []
        result = self.collection.query(
            query_embeddings=[embedder.embed_query(question)],
            n_results=min(k, total),
            where={"video_id": video_id} if video_id is not None else None,
            include=["documents", "metadatas", "distances"],
        )
        return [
            to_hit(doc, meta, dist)
            for doc, meta, dist in zip(
                result["documents"][0], result["metadatas"][0], result["distances"][0], strict=True
            )
        ]

    def delete_video(self, video_id: int) -> None:
        self.collection.delete(where={"video_id": video_id})

    def count(self, video_id: int | None = None) -> int:
        if video_id is None:
            return self.collection.count()
        return len(self.collection.get(where={"video_id": video_id}, include=[])["ids"])

    def info(self) -> dict[str, Any]:
        return {
            "collection": self.name,
            "path": self.path,
            "chunks": self.count(),
            "embedding_model": (self.collection.metadata or {}).get("embedding_model"),
            "distance": (self.collection.metadata or {}).get("hnsw:space"),
        }


def to_hit(doc: str, meta: dict[str, Any], distance: float) -> Hit:
    return Hit(
        video_id=int(meta["video_id"]),
        position=int(meta["position"]),
        start=float(meta["start"]),
        end=float(meta["end"]),
        text=doc,
        score=round(1 - distance, 4),
        title=str(meta.get("title") or ""),
    )


_override: ChromaStore | None = None
_init_lock = threading.Lock()


@lru_cache
def _default_store() -> ChromaStore:
    return ChromaStore(settings.CHROMA_DIR, settings.CHROMA_COLLECTION)


def get_store() -> ChromaStore:
    if _override is not None:
        return _override
    with _init_lock:
        return _default_store()


def set_store(store: ChromaStore | None) -> None:
    global _override
    _override = store
