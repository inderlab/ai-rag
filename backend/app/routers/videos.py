from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.ingestion.youtube import extract_video_id, fmt_ts
from app.models import TranscriptSegment, Video, VideoStatus
from app.services.ingest import ingest_video

router = APIRouter(prefix="/videos", tags=["videos"])

DbSession = Annotated[Session, Depends(get_db)]


class VideoCreate(BaseModel):
    url: str = Field(min_length=5, max_length=500)


class VideoOut(BaseModel):
    id: int
    youtube_id: str
    url: str
    title: str | None
    channel: str | None
    status: VideoStatus
    error: str | None
    language: str | None
    is_generated: bool | None
    segment_count: int
    duration_seconds: float | None
    duration: str | None
    thumbnail_url: str
    created_at: datetime
    updated_at: datetime


class SegmentOut(BaseModel):
    position: int
    start: float
    end: float
    timestamp: str
    text: str


class TranscriptPage(BaseModel):
    video_id: int
    total: int
    offset: int
    limit: int
    segments: list[SegmentOut]


def to_out(video: Video) -> VideoOut:
    return VideoOut(
        id=video.id,
        youtube_id=video.youtube_id,
        url=video.url,
        title=video.title,
        channel=video.channel,
        status=video.status,
        error=video.error,
        language=video.language,
        is_generated=video.is_generated,
        segment_count=video.segment_count,
        duration_seconds=video.duration_seconds,
        duration=fmt_ts(video.duration_seconds) if video.duration_seconds else None,
        thumbnail_url=f"https://i.ytimg.com/vi/{video.youtube_id}/hqdefault.jpg",
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def get_video_or_404(video_id: int, session: Session) -> Video:
    video = session.get(Video, video_id)
    if video is None:
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
def add_video(
    body: VideoCreate,
    background: BackgroundTasks,
    response: Response,
    session: DbSession,
) -> VideoOut:
    youtube_id = extract_video_id(body.url)
    if not youtube_id:
        raise HTTPException(status_code=400, detail="Not a valid YouTube URL")

    existing = session.scalar(select(Video).where(Video.youtube_id == youtube_id))
    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return to_out(existing)

    video = Video(youtube_id=youtube_id, url=f"https://www.youtube.com/watch?v={youtube_id}")
    session.add(video)
    session.commit()
    background.add_task(ingest_video, video.id)
    return to_out(video)


@router.get("", response_model=list[VideoOut])
def list_videos(
    session: DbSession,
    status_filter: Annotated[VideoStatus | None, Query(alias="status")] = None,
) -> list[VideoOut]:
    query = select(Video).order_by(Video.created_at.desc(), Video.id.desc())
    if status_filter is not None:
        query = query.where(Video.status == status_filter)
    return [to_out(v) for v in session.scalars(query)]


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, session: DbSession) -> VideoOut:
    return to_out(get_video_or_404(video_id, session))


@router.get("/{video_id}/transcript", response_model=TranscriptPage)
def get_video_transcript(
    video_id: int,
    session: DbSession,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    q: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
) -> TranscriptPage:
    video = get_video_or_404(video_id, session)
    if video.status != VideoStatus.READY:
        raise HTTPException(
            status_code=409, detail=f"Transcript not ready, video status is '{video.status}'"
        )

    where = [TranscriptSegment.video_id == video.id]
    if q:
        where.append(TranscriptSegment.text.ilike(f"%{q}%"))
    total = session.scalar(select(func.count()).select_from(TranscriptSegment).where(*where)) or 0
    rows = session.scalars(
        select(TranscriptSegment)
        .where(*where)
        .order_by(TranscriptSegment.position)
        .offset(offset)
        .limit(limit)
    )
    return TranscriptPage(
        video_id=video.id,
        total=total,
        offset=offset,
        limit=limit,
        segments=[
            SegmentOut(
                position=s.position,
                start=s.start,
                end=s.end,
                timestamp=fmt_ts(s.start),
                text=s.text,
            )
            for s in rows
        ],
    )


@router.post("/{video_id}/retry", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
def retry_video(video_id: int, background: BackgroundTasks, session: DbSession) -> VideoOut:
    video = get_video_or_404(video_id, session)
    if video.status != VideoStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed videos can be retried")
    video.status = VideoStatus.PENDING
    video.error = None
    session.commit()
    background.add_task(ingest_video, video.id)
    return to_out(video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, session: DbSession) -> Response:
    session.delete(get_video_or_404(video_id, session))
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
