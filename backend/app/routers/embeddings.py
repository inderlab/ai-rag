import math
import threading
import time
from collections import OrderedDict
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.ingestion import embedder
from app.ingestion.embedder import Kind
from app.ingestion.youtube import fmt_ts
from app.models import TranscriptSegment, Video, VideoStatus

router = APIRouter(tags=["embeddings"])

DbSession = Annotated[Session, Depends(get_db)]

CACHE_SIZE = 5
_cache: OrderedDict[tuple[int, str], list[list[float]]] = OrderedDict()
_cache_lock = threading.Lock()


class InfoResponse(BaseModel):
    model: str
    loaded: bool
    dimension: int | None


class EmbedRequest(BaseModel):
    texts: list[str] = Field(
        default_factory=lambda: ["database kaise connect karein", "aaj mausam achha hai"],
        min_length=1,
        max_length=64,
    )
    kind: Kind = "passage"
    full: bool = False


class EmbeddingItem(BaseModel):
    text: str
    preview: list[float]
    norm: float
    vector: list[float] | None = None


class EmbedResponse(BaseModel):
    model: str
    dimension: int
    kind: Kind
    latency_ms: int
    items: list[EmbeddingItem]


class SimilarityRequest(BaseModel):
    query: str = Field("database kaise connect karein", min_length=1, max_length=500)
    passages: list[str] = Field(
        default_factory=lambda: [
            "application.properties mein datasource URL set karo",
            "aaj mausam bahut achha hai",
            "डेटाबेस कनेक्शन के लिए URL सेट करें",
            "cricket match kal shaam 7 baje hai",
        ],
        min_length=1,
        max_length=50,
    )


class ScoredPassage(BaseModel):
    rank: int
    index: int
    text: str
    score: float


class SimilarityResponse(BaseModel):
    model: str
    query: str
    latency_ms: int
    results: list[ScoredPassage]


class SemanticSearchRequest(BaseModel):
    q: str = Field(min_length=2, max_length=300)
    k: int = Field(5, ge=1, le=20)


class SegmentHit(BaseModel):
    rank: int
    position: int
    timestamp: str
    text: str
    score: float
    keyword_match: bool


class SemanticSearchResponse(BaseModel):
    video_id: int
    q: str
    segments_embedded: int
    cached: bool
    latency_ms: int
    results: list[SegmentHit]


def model_or_503() -> embedder.EmbeddingModel:
    try:
        return embedder.get_model()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding model failed to load: {e}") from e


def segment_vectors(video: Video, texts: list[str]) -> tuple[list[list[float]], bool]:
    key = (video.id, video.updated_at.isoformat())
    with _cache_lock:
        if key in _cache:
            _cache.move_to_end(key)
            return _cache[key], True
    vectors = embedder.embed(texts, kind="passage")
    with _cache_lock:
        _cache[key] = vectors
        while len(_cache) > CACHE_SIZE:
            _cache.popitem(last=False)
    return vectors, False


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


@router.get("/embeddings/info", response_model=InfoResponse)
def info() -> InfoResponse:
    loaded = embedder.is_loaded()
    return InfoResponse(
        model=embedder.get_model().name if loaded else settings.EMBEDDING_MODEL,
        loaded=loaded,
        dimension=embedder.get_model().dimension if loaded else None,
    )


@router.post("/embeddings", response_model=EmbedResponse)
def create_embeddings(body: EmbedRequest) -> EmbedResponse:
    model = model_or_503()
    start = time.perf_counter()
    vectors = embedder.embed(body.texts, kind=body.kind)
    latency = int((time.perf_counter() - start) * 1000)
    return EmbedResponse(
        model=model.name,
        dimension=model.dimension,
        kind=body.kind,
        latency_ms=latency,
        items=[
            EmbeddingItem(
                text=text,
                preview=[round(x, 4) for x in vec[:8]],
                norm=round(math.sqrt(sum(x * x for x in vec)), 4),
                vector=vec if body.full else None,
            )
            for text, vec in zip(body.texts, vectors, strict=True)
        ],
    )


@router.post("/embeddings/similarity", response_model=SimilarityResponse)
def similarity(body: SimilarityRequest) -> SimilarityResponse:
    model = model_or_503()
    start = time.perf_counter()
    ranked = embedder.rank(body.query, body.passages)
    latency = int((time.perf_counter() - start) * 1000)
    return SimilarityResponse(
        model=model.name,
        query=body.query,
        latency_ms=latency,
        results=[
            ScoredPassage(rank=r, index=i, text=body.passages[i], score=round(score, 4))
            for r, (i, score) in enumerate(ranked, start=1)
        ],
    )


@router.post("/videos/{video_id}/semantic-search", response_model=SemanticSearchResponse)
def semantic_search(
    video_id: int, body: SemanticSearchRequest, session: DbSession
) -> SemanticSearchResponse:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    if video.status != VideoStatus.READY:
        raise HTTPException(
            status_code=409, detail=f"Transcript not ready, video status is '{video.status}'"
        )
    model_or_503()

    segments = list(
        session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.video_id == video.id)
            .order_by(TranscriptSegment.position)
        )
    )
    start = time.perf_counter()
    vectors, cached = segment_vectors(video, [s.text for s in segments])
    q = embedder.embed_query(body.q)
    scored = sorted(
        ((i, embedder.cosine(q, v)) for i, v in enumerate(vectors)),
        key=lambda x: x[1],
        reverse=True,
    )[: body.k]
    latency = int((time.perf_counter() - start) * 1000)

    words = [w.lower() for w in body.q.split() if len(w) > 2]
    return SemanticSearchResponse(
        video_id=video.id,
        q=body.q,
        segments_embedded=len(segments),
        cached=cached,
        latency_ms=latency,
        results=[
            SegmentHit(
                rank=r,
                position=segments[i].position,
                timestamp=fmt_ts(segments[i].start),
                text=segments[i].text,
                score=round(score, 4),
                keyword_match=any(w in segments[i].text.lower() for w in words),
            )
            for r, (i, score) in enumerate(scored, start=1)
        ],
    )
