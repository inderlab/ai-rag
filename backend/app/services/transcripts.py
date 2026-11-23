from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import can_see
from app.config import settings
from app.ingestion.chunker import Chunk, chunk_segments
from app.models import TranscriptSegment, User, Video, VideoStatus


def visible_video(session: Session, video_id: int, user: User | None) -> Video:
    video = session.get(Video, video_id)
    if video is None or not can_see(video, user):
        raise HTTPException(status_code=404, detail="Video not found")
    return video


def ready_video(session: Session, video_id: int, user: User | None = None) -> Video:
    video = visible_video(session, video_id, user)
    if video.status != VideoStatus.READY:
        raise HTTPException(
            status_code=409, detail=f"Transcript not ready, video status is '{video.status}'"
        )
    return video


def load_segments(session: Session, video: Video) -> list[TranscriptSegment]:
    return list(
        session.scalars(
            select(TranscriptSegment)
            .where(TranscriptSegment.video_id == video.id)
            .order_by(TranscriptSegment.position)
        )
    )


def video_chunks(
    session: Session,
    video: Video,
    max_words: int | None = None,
    overlap_words: int | None = None,
) -> list[Chunk]:
    segments = load_segments(session, video)
    return chunk_segments(
        [{"text": s.text, "start": s.start, "end": s.end} for s in segments],
        max_words or settings.CHUNK_MAX_WORDS,
        settings.CHUNK_OVERLAP_WORDS if overlap_words is None else overlap_words,
    )
