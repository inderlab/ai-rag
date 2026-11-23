from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.config import settings
from app.db import get_db
from app.ingestion import chunker
from app.ingestion.youtube import fmt_ts
from app.services.transcripts import ready_video, video_chunks

router = APIRouter(tags=["chunks"])

DbSession = Annotated[Session, Depends(get_db)]

SAMPLE_TEXT = (
    "Spring Boot mein database connect karne ke liye pehle dependency add karo. "
    "Phir application.properties mein datasource URL, username aur password likho. "
    "Ab JPA entity banao aur repository interface likho. "
    "Server start karo aur logs mein connection pool check karo."
)


class Stats(BaseModel):
    count: int
    avg_words: float
    min_words: int
    max_words: int


class PreviewRequest(BaseModel):
    text: str = Field(SAMPLE_TEXT, min_length=1, max_length=100_000)
    max_words: int = Field(12, ge=1, le=2000)
    overlap_words: int = Field(3, ge=0)

    @model_validator(mode="after")
    def overlap_smaller(self) -> "PreviewRequest":
        if self.overlap_words >= self.max_words:
            raise ValueError("overlap_words must be smaller than max_words")
        return self


class PreviewChunk(BaseModel):
    position: int
    word_count: int
    text: str


class PreviewResponse(BaseModel):
    total_words: int
    max_words: int
    overlap_words: int
    count: int
    chunks: list[PreviewChunk]


class ChunkOut(BaseModel):
    position: int
    start: float
    end: float
    timestamp: str
    end_timestamp: str
    word_count: int
    first_segment: int
    last_segment: int
    shared_with_previous: int
    text: str


class VideoChunksResponse(BaseModel):
    video_id: int
    segment_count: int
    max_words: int
    overlap_words: int
    stats: Stats
    chunks: list[ChunkOut]


class SizeResult(BaseModel):
    max_words: int
    overlap_words: int
    stats: Stats
    first_chunk: str


class CompareResponse(BaseModel):
    video_id: int
    segment_count: int
    sizes: list[SizeResult]


def to_out(chunks: list[chunker.Chunk]) -> list[ChunkOut]:
    return [
        ChunkOut(
            position=c.position,
            start=c.start,
            end=c.end,
            timestamp=fmt_ts(c.start),
            end_timestamp=fmt_ts(c.end),
            word_count=c.word_count,
            first_segment=c.first_segment,
            last_segment=c.last_segment,
            shared_with_previous=chunker.shared_segments(chunks[i - 1], c) if i else 0,
            text=c.text,
        )
        for i, c in enumerate(chunks)
    ]


def overlap_for(max_words: int, overlap_words: int | None) -> int:
    overlap = settings.CHUNK_OVERLAP_WORDS if overlap_words is None else overlap_words
    if overlap >= max_words:
        raise HTTPException(status_code=422, detail="overlap_words must be smaller than max_words")
    return overlap


@router.post("/chunks/preview", response_model=PreviewResponse)
def preview(body: PreviewRequest) -> PreviewResponse:
    parts = chunker.chunk_words(body.text, body.max_words, body.overlap_words)
    return PreviewResponse(
        total_words=len(body.text.split()),
        max_words=body.max_words,
        overlap_words=body.overlap_words,
        count=len(parts),
        chunks=[
            PreviewChunk(position=i, word_count=len(p.split()), text=p) for i, p in enumerate(parts)
        ],
    )


@router.get("/videos/{video_id}/chunks", response_model=VideoChunksResponse)
def list_chunks(
    video_id: int,
    session: DbSession,
    user: CurrentUser,
    max_words: Annotated[int, Query(ge=10, le=2000)] = settings.CHUNK_MAX_WORDS,
    overlap_words: Annotated[int | None, Query(ge=0)] = None,
) -> VideoChunksResponse:
    video = ready_video(session, video_id, user)
    overlap = overlap_for(max_words, overlap_words)
    chunks = video_chunks(session, video, max_words, overlap)
    return VideoChunksResponse(
        video_id=video.id,
        segment_count=video.segment_count,
        max_words=max_words,
        overlap_words=overlap,
        stats=Stats(**chunker.stats(chunks)),
        chunks=to_out(chunks),
    )


@router.get("/videos/{video_id}/chunks/compare", response_model=CompareResponse)
def compare_sizes(
    video_id: int,
    session: DbSession,
    user: CurrentUser,
    sizes: Annotated[str, Query(pattern=r"^\d+(,\d+){0,5}$")] = "100,300,800",
) -> CompareResponse:
    video = ready_video(session, video_id, user)
    results = []
    for size in (int(s) for s in sizes.split(",")):
        if not 10 <= size <= 2000:
            raise HTTPException(status_code=422, detail="Each size must be between 10 and 2000")
        overlap = min(settings.CHUNK_OVERLAP_WORDS, size // 5)
        chunks = video_chunks(session, video, size, overlap)
        first = chunks[0] if chunks else None
        results.append(
            SizeResult(
                max_words=size,
                overlap_words=overlap,
                stats=Stats(**chunker.stats(chunks)),
                first_chunk=f"{fmt_ts(first.start)} - {fmt_ts(first.end)}" if first else "",
            )
        )
    return CompareResponse(video_id=video.id, segment_count=video.segment_count, sizes=results)
