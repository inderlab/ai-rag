import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.db import get_db
from app.llm.factory import get_llm
from app.models import VideoInsightsRow
from app.services import insights as insights_service
from app.services.insights import Chapter
from app.services.rag import to_seconds
from app.services.transcripts import ready_video

log = logging.getLogger(__name__)

router = APIRouter(prefix="/videos", tags=["insights"])

DbSession = Annotated[Session, Depends(get_db)]


class ChapterOut(Chapter):
    seconds: int


class InsightsOut(BaseModel):
    video_id: int
    title: str
    summary: str
    chapters: list[ChapterOut]
    tags: list[str]
    key_points: list[str]
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    created_at: datetime


class GenerateRequest(BaseModel):
    provider: str | None = None


def to_out(row: VideoInsightsRow) -> InsightsOut:
    return InsightsOut(
        video_id=row.video_id,
        title=row.title,
        summary=row.summary,
        chapters=[
            ChapterOut(start=c["start"], title=c["title"], seconds=to_seconds(c["start"]))
            for c in row.chapters
        ],
        tags=row.tags,
        key_points=row.key_points or [],
        provider=row.provider,
        model=row.model,
        input_tokens=row.input_tokens,
        output_tokens=row.output_tokens,
        created_at=row.created_at,
    )


@router.get("/{video_id}/insights", response_model=InsightsOut)
def get_insights(video_id: int, session: DbSession, user: CurrentUser) -> InsightsOut:
    video = ready_video(session, video_id, user)
    if video.insights is None:
        raise HTTPException(status_code=404, detail="No insights yet, POST to generate them")
    return to_out(video.insights)


@router.post("/{video_id}/insights", response_model=InsightsOut)
def generate_insights(
    video_id: int, session: DbSession, user: CurrentUser, body: GenerateRequest | None = None
) -> InsightsOut:
    video = ready_video(session, video_id, user)
    try:
        llm = get_llm(body.provider if body else None)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    try:
        row = insights_service.create_insights(session, video, llm)
    except Exception as e:
        log.exception("insights failed for video %s", video_id)
        raise HTTPException(status_code=502, detail=f"{llm.name} call failed: {e}") from e
    return to_out(row)
