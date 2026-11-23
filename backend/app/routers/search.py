import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser, scope_id
from app.config import settings
from app.db import get_db
from app.ingestion.youtube import fmt_ts
from app.models import Video
from app.services.transcripts import visible_video
from app.vectorstore.chroma_store import ChromaStore, Hit, get_store

router = APIRouter(tags=["search"])

DbSession = Annotated[Session, Depends(get_db)]


class SearchHit(BaseModel):
    rank: int
    video_id: int
    title: str
    position: int
    start: float
    end: float
    timestamp: str
    end_timestamp: str
    url: str
    score: float
    text: str


class SearchResponse(BaseModel):
    q: str
    video_id: int | None
    k: int
    latency_ms: int
    results: list[SearchHit]


class StoreInfo(BaseModel):
    collection: str
    path: str
    chunks: int
    embedding_model: str | None
    distance: str | None


def store_or_503() -> ChromaStore:
    try:
        return get_store()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Vector store unavailable: {e}") from e


def to_search_hit(rank: int, hit: Hit, video: Video | None) -> SearchHit:
    youtube_id = video.youtube_id if video else ""
    return SearchHit(
        rank=rank,
        video_id=hit.video_id,
        title=(video.title if video else None) or hit.title,
        position=hit.position,
        start=hit.start,
        end=hit.end,
        timestamp=fmt_ts(hit.start),
        end_timestamp=fmt_ts(hit.end),
        url=f"https://www.youtube.com/watch?v={youtube_id}&t={int(hit.start)}s"
        if youtube_id
        else "",
        score=hit.score,
        text=hit.text,
    )


@router.get("/vectorstore/info", response_model=StoreInfo)
def info() -> StoreInfo:
    return StoreInfo(**store_or_503().info())


@router.get("/search", response_model=SearchResponse)
def search(
    session: DbSession,
    user: CurrentUser,
    q: Annotated[str, Query(min_length=2, max_length=300)],
    video_id: int | None = None,
    k: Annotated[int, Query(ge=1, le=20)] = settings.SEARCH_K,
) -> SearchResponse:
    if video_id is not None:
        visible_video(session, video_id, user)
    store = store_or_503()
    start = time.perf_counter()
    hits = store.search(q, video_id=video_id, k=k, user_id=scope_id(user))
    latency = int((time.perf_counter() - start) * 1000)
    videos = {h.video_id: session.get(Video, h.video_id) for h in hits}
    return SearchResponse(
        q=q,
        video_id=video_id,
        k=k,
        latency_ms=latency,
        results=[to_search_hit(r, h, videos[h.video_id]) for r, h in enumerate(hits, start=1)],
    )
