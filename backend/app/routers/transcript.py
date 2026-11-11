from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.ingestion.youtube import extract_video_id, fetch_transcript, fmt_ts

router = APIRouter(tags=["transcript"])


class Segment(BaseModel):
    text: str
    start: float
    end: float
    timestamp: str


class TranscriptResponse(BaseModel):
    video_id: str
    segment_count: int
    segments: list[Segment]


@router.get("/transcript", response_model=TranscriptResponse)
def get_transcript(
    url: str = Query(..., description="Any YouTube link or an 11-char video id"),
    limit: int = Query(50, ge=1, le=2000),
) -> TranscriptResponse:
    video_id = extract_video_id(url)
    if not video_id:
        raise HTTPException(status_code=400, detail="Not a valid YouTube URL")

    try:
        segments = fetch_transcript(video_id)
    except Exception as e:  # no captions, private video, blocked request
        raise HTTPException(status_code=404, detail=f"Could not get captions: {e}") from e

    return TranscriptResponse(
        video_id=video_id,
        segment_count=len(segments),
        segments=[Segment(**s, timestamp=fmt_ts(s["start"])) for s in segments[:limit]],
    )
