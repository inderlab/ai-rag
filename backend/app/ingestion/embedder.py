import math
import threading
from collections.abc import Sequence
from functools import lru_cache
from typing import Literal, Protocol

from app.config import settings

Kind = Literal["query", "passage"]


class EmbeddingModel(Protocol):
    name: str
    dimension: int

    def encode(self, texts: list[str]) -> list[list[float]]: ...


class SentenceTransformerModel:
    def __init__(self, name: str, batch_size: int = 32):
        from sentence_transformers import SentenceTransformer

        self.name = name
        self.batch_size = batch_size
        self._model = SentenceTransformer(name)
        self.dimension = self._model.get_embedding_dimension()
        self._lock = threading.Lock()

    def encode(self, texts: list[str]) -> list[list[float]]:
        with self._lock:
            vectors = self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )
        return vectors.tolist()


_override: EmbeddingModel | None = None


@lru_cache
def _default_model() -> EmbeddingModel:
    return SentenceTransformerModel(settings.EMBEDDING_MODEL, settings.EMBEDDING_BATCH_SIZE)


def get_model() -> EmbeddingModel:
    return _override or _default_model()


def set_model(model: EmbeddingModel | None) -> None:
    global _override
    _override = model


def is_loaded() -> bool:
    return _override is not None or _default_model.cache_info().currsize > 0


def add_prefix(text: str, kind: Kind) -> str:
    return f"{kind}: {' '.join(text.split())}"


def embed(texts: Sequence[str], kind: Kind = "passage") -> list[list[float]]:
    if not texts:
        return []
    return get_model().encode([add_prefix(t, kind) for t in texts])


def embed_query(text: str) -> list[float]:
    return embed([text], kind="query")[0]


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Vector sizes differ: {len(a)} vs {len(b)}")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def rank(query: str, passages: Sequence[str]) -> list[tuple[int, float]]:
    q = embed_query(query)
    vectors = embed(passages, kind="passage")
    scores = [(i, cosine(q, v)) for i, v in enumerate(vectors)]
    return sorted(scores, key=lambda x: x[1], reverse=True)
