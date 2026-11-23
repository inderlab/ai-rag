import mimetypes
import uuid
from datetime import datetime
from pathlib import Path
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser, can_see
from app.config import settings
from app.db import get_db
from app.ingestion.youtube import extract_video_id, fmt_ts
from app.models import TranscriptSegment, User, Video, VideoStatus
from app.services.ingest import ingest_video, reindex_video
from app.vectorstore.chroma_store import get_store

router = APIRouter(prefix="/videos", tags=["videos"])

DbSession = Annotated[Session, Depends(get_db)]

ALLOWED_TYPES = {".mp4", ".mov", ".webm", ".mkv", ".mp3", ".m4a", ".wav", ".ogg"}
CHUNK_BYTES = 1024 * 1024


class VideoCreate(BaseModel):
    url: str = Field(min_length=5, max_length=500)


class VideoOut(BaseModel):
    id: int
    source: str
    private: bool
    media_url: str | None
    youtube_id: str
    url: str
    title: str | None
    channel: str | None
    status: VideoStatus
    error: str | None
    language: str | None
    is_generated: bool | None
    segment_count: int
    chunk_count: int
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
    upload = video.source == "upload"
    return VideoOut(
        id=video.id,
        source=video.source,
        private=video.user_id is not None,
        media_url=f"/api/videos/{video.id}/media" if upload else None,
        youtube_id=video.youtube_id,
        url=video.url,
        title=video.title,
        channel=video.channel,
        status=video.status,
        error=video.error,
        language=video.language,
        is_generated=video.is_generated,
        segment_count=video.segment_count,
        chunk_count=video.chunk_count or 0,
        duration_seconds=video.duration_seconds,
        duration=fmt_ts(video.duration_seconds) if video.duration_seconds else None,
        thumbnail_url="" if upload else f"https://i.ytimg.com/vi/{video.youtube_id}/hqdefault.jpg",
        created_at=video.created_at,
        updated_at=video.updated_at,
    )


def get_video_or_404(video_id: int, session: Session, user: User | None = None) -> Video:
    video = session.get(Video, video_id)
    if video is None or not can_see(video, user):
        raise HTTPException(status_code=404, detail="Video not found")
    return video


@router.post("", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
def add_video(
    body: VideoCreate,
    background: BackgroundTasks,
    response: Response,
    session: DbSession,
    user: CurrentUser,
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
    user: CurrentUser,
    status_filter: Annotated[VideoStatus | None, Query(alias="status")] = None,
) -> list[VideoOut]:
    query = select(Video).order_by(Video.created_at.desc(), Video.id.desc())
    if status_filter is not None:
        query = query.where(Video.status == status_filter)
    if user is None:
        query = query.where(Video.user_id.is_(None))
    else:
        query = query.where(or_(Video.user_id.is_(None), Video.user_id == user.id))
    return [to_out(v) for v in session.scalars(query)]


@router.get("/{video_id}", response_model=VideoOut)
def get_video(video_id: int, session: DbSession, user: CurrentUser) -> VideoOut:
    return to_out(get_video_or_404(video_id, session, user))


@router.get("/{video_id}/transcript", response_model=TranscriptPage)
def get_video_transcript(
    video_id: int,
    session: DbSession,
    user: CurrentUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    q: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
) -> TranscriptPage:
    video = get_video_or_404(video_id, session, user)
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
def retry_video(
    video_id: int, background: BackgroundTasks, session: DbSession, user: CurrentUser
) -> VideoOut:
    video = get_video_or_404(video_id, session, user)
    if video.status != VideoStatus.FAILED:
        raise HTTPException(status_code=409, detail="Only failed videos can be retried")
    video.status = VideoStatus.PENDING
    video.error = None
    session.commit()
    background.add_task(ingest_video, video.id)
    return to_out(video)


@router.post("/{video_id}/reindex", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
def reindex(
    video_id: int, background: BackgroundTasks, session: DbSession, user: CurrentUser
) -> VideoOut:
    video = get_video_or_404(video_id, session, user)
    if video.status not in (VideoStatus.READY, VideoStatus.FAILED) or not video.segment_count:
        raise HTTPException(status_code=409, detail="Video needs a saved transcript to re-index")
    background.add_task(reindex_video, video.id)
    return to_out(video)


@router.delete("/{video_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_video(video_id: int, session: DbSession, user: CurrentUser) -> Response:
    video = get_video_or_404(video_id, session, user)
    get_store().delete_video(video.id)
    if video.file_path:
        Path(video.file_path).unlink(missing_ok=True)
    session.delete(video)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def save_upload(file: UploadFile, suffix: str) -> Path:
    folder = Path(settings.UPLOAD_DIR)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{uuid.uuid4().hex}{suffix}"
    limit = settings.UPLOAD_MAX_MB * 1024 * 1024
    size = 0
    with target.open("wb") as out:
        while chunk := file.file.read(CHUNK_BYTES):
            size += len(chunk)
            if size > limit:
                out.close()
                target.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=413, detail=f"File is larger than {settings.UPLOAD_MAX_MB} MB"
                )
            out.write(chunk)
    if size == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="The file is empty")
    return target


@router.post("/upload", response_model=VideoOut, status_code=status.HTTP_202_ACCEPTED)
def upload_video(
    background: BackgroundTasks,
    session: DbSession,
    user: CurrentUser,
    file: Annotated[UploadFile, File()],
    title: Annotated[str | None, Form(max_length=300)] = None,
) -> VideoOut:
    name = Path(file.filename or "video").name
    suffix = Path(name).suffix.lower()
    if suffix not in ALLOWED_TYPES:
        allowed = ", ".join(sorted(ALLOWED_TYPES))
        raise HTTPException(status_code=415, detail=f"Unsupported file type. Use one of: {allowed}")
    path = save_upload(file, suffix)
    video = Video(
        source="upload",
        youtube_id=f"u{uuid.uuid4().hex[:10]}",
        url=f"upload://{name}",
        title=(title or "").strip() or Path(name).stem,
        channel=user.name if user else "Upload",
        user_id=user.id if user else None,
        file_path=str(path),
    )
    session.add(video)
    session.commit()
    background.add_task(ingest_video, video.id)
    return to_out(video)


@router.get("/{video_id}/media")
def video_media(video_id: int, session: DbSession, user: CurrentUser) -> FileResponse:
    video = get_video_or_404(video_id, session, user)
    if video.source != "upload" or not video.file_path or not Path(video.file_path).is_file():
        raise HTTPException(status_code=404, detail="No media file for this video")
    media_type = mimetypes.guess_type(video.file_path)[0] or "application/octet-stream"
    return FileResponse(video.file_path, media_type=media_type)
