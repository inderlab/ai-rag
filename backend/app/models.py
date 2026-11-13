from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.db import Base


class VideoStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(20), default="youtube")
    youtube_id: Mapped[str] = mapped_column(String(11), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str | None] = mapped_column(String(300))
    channel: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[VideoStatus] = mapped_column(
        Enum(VideoStatus, native_enum=False, values_callable=lambda e: [m.value for m in e]),
        default=VideoStatus.PENDING,
        index=True,
    )
    error: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(String(20))
    is_generated: Mapped[bool | None]
    duration_seconds: Mapped[float | None]
    segment_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.position",
    )


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(ForeignKey("videos.id", ondelete="CASCADE"), index=True)
    position: Mapped[int]
    start: Mapped[float]
    end: Mapped[float]
    text: Mapped[str] = mapped_column(Text)

    video: Mapped[Video] = relationship(back_populates="segments")


def init_db() -> None:
    Base.metadata.create_all(db.engine)
