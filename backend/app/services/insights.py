import json
import logging

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import db
from app.config import settings
from app.ingestion.chunker import Chunk
from app.ingestion.youtube import fmt_ts
from app.llm.base import LLMProvider
from app.llm.factory import get_llm
from app.llm.prompts import INSIGHTS_SYSTEM, MERGE_SYSTEM
from app.models import Video, VideoInsightsRow, VideoStatus
from app.services.rag import TIMESTAMP, to_seconds
from app.services.transcripts import load_segments

log = logging.getLogger(__name__)


class Chapter(BaseModel):
    start: str = Field(description="Start time copied from the transcript, like 04:12")
    title: str


class VideoInsights(BaseModel):
    title: str
    summary: str
    chapters: list[Chapter]
    tags: list[str]
    key_points: list[str]


MARKER_SECONDS = 30


def timed_blocks(segments: list, every: float = MARKER_SECONDS) -> list[Chunk]:
    blocks: list[Chunk] = []
    for s in segments:
        words = s.text.split()
        if not words:
            continue
        last = blocks[-1] if blocks else None
        if last is not None and s.start - last.start < every:
            blocks[-1] = Chunk(
                last.position,
                last.start,
                s.end,
                f"{last.text} {' '.join(words)}",
                last.word_count + len(words),
                last.first_segment,
                s.position,
            )
        else:
            blocks.append(
                Chunk(
                    len(blocks), s.start, s.end, " ".join(words), len(words), s.position, s.position
                )
            )
    return blocks


def transcript_text(chunks: list[Chunk]) -> str:
    return "\n\n".join(f"[{fmt_ts(c.start)}] {c.text}" for c in chunks)


def groups(chunks: list[Chunk], max_words: int) -> list[list[Chunk]]:
    out: list[list[Chunk]] = [[]]
    words = 0
    for c in chunks:
        if out[-1] and words + c.word_count > max_words:
            out.append([])
            words = 0
        out[-1].append(c)
        words += c.word_count
    return [g for g in out if g]


def clean(insights: VideoInsights, duration: float | None) -> VideoInsights:
    seen: dict[int, Chapter] = {}
    for ch in insights.chapters:
        ts = ch.start.strip("[] ")
        if not TIMESTAMP.fullmatch(f"[{ts}]"):
            continue
        seconds = to_seconds(ts)
        if duration and seconds > duration:
            continue
        seen.setdefault(seconds, Chapter(start=fmt_ts(seconds), title=ch.title.strip()))
    chapters = [seen[s] for s in sorted(seen)]
    if chapters and chapters[0].start != "00:00":
        chapters[0] = Chapter(start="00:00", title=chapters[0].title)
    tags = []
    for tag in insights.tags:
        t = tag.strip().lstrip("#").lower()
        if t and t not in tags:
            tags.append(t)
    return VideoInsights(
        title=insights.title.strip()[:300],
        summary=insights.summary.strip(),
        chapters=chapters,
        tags=tags[:10],
        key_points=[p.strip() for p in insights.key_points if p.strip()][:6],
    )


def generate(
    llm: LLMProvider, chunks: list[Chunk], max_words: int
) -> tuple[VideoInsights, int, int]:
    parts = groups(chunks, max_words)
    tokens_in = tokens_out = 0
    partials = []
    for part in parts:
        result = llm.structured(
            INSIGHTS_SYSTEM,
            [{"role": "user", "content": f"<transcript>\n{transcript_text(part)}\n</transcript>"}],
            VideoInsights,
        )
        tokens_in += result.input_tokens
        tokens_out += result.output_tokens
        partials.append(result.data)
    if len(partials) == 1:
        return partials[0], tokens_in, tokens_out
    merged = llm.structured(
        MERGE_SYSTEM,
        [
            {
                "role": "user",
                "content": json.dumps([p.model_dump() for p in partials], ensure_ascii=False),
            }
        ],
        VideoInsights,
    )
    return merged.data, tokens_in + merged.input_tokens, tokens_out + merged.output_tokens


def create_insights(session: Session, video: Video, llm: LLMProvider) -> VideoInsightsRow:
    chunks = timed_blocks(load_segments(session, video))
    if not chunks:
        raise ValueError("Video has no transcript to summarise")
    data, tokens_in, tokens_out = generate(llm, chunks, settings.INSIGHTS_MAX_WORDS)
    data = clean(data, video.duration_seconds)
    row = video.insights or VideoInsightsRow(video_id=video.id)
    row.title = data.title
    row.summary = data.summary
    row.chapters = [c.model_dump() for c in data.chapters]
    row.tags = data.tags
    row.key_points = data.key_points
    row.provider = llm.name
    row.model = llm.model
    row.input_tokens = tokens_in
    row.output_tokens = tokens_out
    session.add(row)
    session.commit()
    log.info(
        "insights video=%s provider=%s model=%s in=%s out=%s",
        video.id,
        llm.name,
        llm.model,
        tokens_in,
        tokens_out,
    )
    return row


def auto_insights(video_id: int) -> None:
    if not settings.AUTO_INSIGHTS:
        return
    try:
        llm = get_llm()
    except ValueError as e:
        log.info("skipping insights: %s", e)
        return
    with db.SessionLocal() as session:
        video = session.get(Video, video_id)
        if video is None or video.status != VideoStatus.READY:
            return
        try:
            create_insights(session, video, llm)
        except Exception:
            log.exception("insights failed for video %s", video_id)
