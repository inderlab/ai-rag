import logging
from typing import Any

import httpx

from app import db
from app.config import settings
from app.models import Video, VideoStatus

log = logging.getLogger(__name__)


def payload(video: Video) -> dict[str, Any]:
    insights = video.insights
    return {
        "event": "video.ready" if video.status == VideoStatus.READY else "video.failed",
        "video": {
            "id": video.id,
            "youtube_id": video.youtube_id,
            "title": video.title,
            "channel": video.channel,
            "status": str(video.status),
            "error": video.error,
            "duration_seconds": video.duration_seconds,
            "chunk_count": video.chunk_count,
            "url": video.url,
            "app_url": f"{settings.PUBLIC_APP_URL}/videos/{video.id}",
        },
        "insights": {
            "title": insights.title,
            "summary": insights.summary,
            "tags": insights.tags,
            "chapters": insights.chapters,
        }
        if insights
        else None,
    }


def notify(video_id: int) -> bool:
    if not settings.N8N_WEBHOOK_URL:
        return False
    with db.SessionLocal() as session:
        video = session.get(Video, video_id)
        if video is None or video.status not in (VideoStatus.READY, VideoStatus.FAILED):
            return False
        body = payload(video)
    try:
        r = httpx.post(settings.N8N_WEBHOOK_URL, json=body, timeout=10)
        r.raise_for_status()
    except httpx.HTTPError as e:
        log.warning("n8n webhook failed for video %s: %s", video_id, e)
        return False
    return True
