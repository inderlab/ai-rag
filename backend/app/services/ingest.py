import logging
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app import db
from app.config import settings
from app.ingestion import whisper, youtube
from app.ingestion.chunker import chunk_segments
from app.models import TranscriptSegment, Video, VideoStatus
from app.services import hooks
from app.services.insights import auto_insights
from app.vectorstore.chroma_store import get_store

log = logging.getLogger(__name__)


def index_video(video: Video) -> int:
    segments = sorted(video.segments, key=lambda s: s.position)
    chunks = chunk_segments(
        [{"text": s.text, "start": s.start, "end": s.end} for s in segments],
        settings.CHUNK_MAX_WORDS,
        settings.CHUNK_OVERLAP_WORDS,
    )
    count = get_store().add_chunks(video.id, chunks, title=video.title or "", user_id=video.user_id)
    video.chunk_count = count
    return count


def run_indexing(session: Session, video: Video) -> bool:
    video.status = VideoStatus.INDEXING
    session.commit()
    try:
        index_video(video)
    except Exception as e:
        log.exception("indexing failed for video %s", video.id)
        video.status = VideoStatus.FAILED
        video.error = f"Indexing failed: {e}"[:500]
        session.commit()
        return False
    video.status = VideoStatus.READY
    session.commit()
    return True


@dataclass
class Source:
    segments: list[dict]
    language: str | None
    is_generated: bool | None
    title: str | None = None
    channel: str | None = None


class SourceError(RuntimeError):
    pass


def from_youtube(video: Video) -> Source:
    try:
        captions = youtube.fetch_captions(video.youtube_id)
    except Exception as e:
        log.warning("captions failed for %s: %s", video.youtube_id, e)
        raise SourceError(youtube.friendly_error(e)) from e
    if not captions.segments:
        raise SourceError("Captions were found but they are empty")
    try:
        meta = youtube.fetch_metadata(video.youtube_id)
    except Exception as e:
        log.info("metadata failed for %s: %s", video.youtube_id, e)
        meta = {}
    return Source(
        captions.segments,
        captions.language,
        captions.is_generated,
        meta.get("title"),
        meta.get("channel"),
    )


def from_upload(video: Video) -> Source:
    path = Path(video.file_path or "")
    if not path.is_file():
        raise SourceError("Uploaded file is missing on the server")
    try:
        result = whisper.get_transcriber().transcribe(path)
    except whisper.AudioError as e:
        raise SourceError(str(e)) from e
    except Exception as e:
        log.exception("whisper failed for video %s", video.id)
        raise SourceError(f"Transcription failed: {e}") from e
    if not result.segments:
        raise SourceError("No speech was found in the file")
    return Source(result.segments, result.language, True)


def fetch_and_index(video_id: int) -> bool | None:
    with db.SessionLocal() as session:
        video = session.get(Video, video_id)
        if video is None or video.status == VideoStatus.READY:
            return None

        video.status = VideoStatus.PROCESSING
        video.error = None
        session.commit()

        try:
            source = from_upload(video) if video.source == "upload" else from_youtube(video)
        except SourceError as e:
            video.status = VideoStatus.FAILED
            video.error = str(e)
            session.commit()
            return False

        session.execute(delete(TranscriptSegment).where(TranscriptSegment.video_id == video.id))
        session.add_all(
            TranscriptSegment(video_id=video.id, position=i, **seg)
            for i, seg in enumerate(source.segments)
        )
        video.title = source.title or video.title
        video.channel = source.channel or video.channel
        video.language = source.language
        video.is_generated = source.is_generated
        video.segment_count = len(source.segments)
        video.duration_seconds = source.segments[-1]["end"]
        session.commit()
        session.refresh(video)

        return run_indexing(session, video)


def ingest_video(video_id: int) -> None:
    ready = fetch_and_index(video_id)
    if ready is None:
        return
    if ready:
        auto_insights(video_id)
    hooks.notify(video_id)


def reindex_video(video_id: int) -> None:
    with db.SessionLocal() as session:
        video = session.get(Video, video_id)
        if video is None or not video.segments:
            return
        run_indexing(session, video)
