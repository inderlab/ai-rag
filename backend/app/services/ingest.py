import logging

from sqlalchemy import delete

from app import db
from app.ingestion import youtube
from app.models import TranscriptSegment, Video, VideoStatus

log = logging.getLogger(__name__)


def ingest_video(video_id: int) -> None:
    with db.SessionLocal() as session:
        video = session.get(Video, video_id)
        if video is None or video.status == VideoStatus.READY:
            return

        video.status = VideoStatus.PROCESSING
        video.error = None
        session.commit()

        try:
            captions = youtube.fetch_captions(video.youtube_id)
        except Exception as e:
            log.warning("captions failed for %s: %s", video.youtube_id, e)
            video.status = VideoStatus.FAILED
            video.error = youtube.friendly_error(e)
            session.commit()
            return

        if not captions.segments:
            video.status = VideoStatus.FAILED
            video.error = "Captions were found but they are empty"
            session.commit()
            return

        try:
            meta = youtube.fetch_metadata(video.youtube_id)
        except Exception as e:
            log.info("metadata failed for %s: %s", video.youtube_id, e)
            meta = {}

        session.execute(delete(TranscriptSegment).where(TranscriptSegment.video_id == video.id))
        session.add_all(
            TranscriptSegment(video_id=video.id, position=i, **seg)
            for i, seg in enumerate(captions.segments)
        )
        video.title = meta.get("title") or video.title
        video.channel = meta.get("channel") or video.channel
        video.language = captions.language
        video.is_generated = captions.is_generated
        video.segment_count = len(captions.segments)
        video.duration_seconds = captions.segments[-1]["end"]
        video.status = VideoStatus.READY
        session.commit()
