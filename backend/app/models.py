from datetime import UTC, datetime
from enum import StrEnum

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, String, Text, inspect, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import db
from app.db import Base


class VideoStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


def utcnow() -> datetime:
    return datetime.now(UTC)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Video(Base):
    __tablename__ = "videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    source: Mapped[str] = mapped_column(String(20), default="youtube")
    file_path: Mapped[str | None] = mapped_column(String(500))
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
    chunk_count: Mapped[int] = mapped_column(default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    segments: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="video",
        cascade="all, delete-orphan",
        order_by="TranscriptSegment.position",
    )
    insights: Mapped["VideoInsightsRow | None"] = relationship(
        back_populates="video", cascade="all, delete-orphan", uselist=False
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


class VideoInsightsRow(Base):
    __tablename__ = "video_insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    video_id: Mapped[int] = mapped_column(
        ForeignKey("videos.id", ondelete="CASCADE"), unique=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    chapters: Mapped[list] = mapped_column(JSON, default=list)
    tags: Mapped[list] = mapped_column(JSON, default=list)
    key_points: Mapped[list] = mapped_column(JSON, default=list)
    provider: Mapped[str] = mapped_column(String(20))
    model: Mapped[str] = mapped_column(String(100))
    input_tokens: Mapped[int] = mapped_column(default=0)
    output_tokens: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    video: Mapped[Video] = relationship(back_populates="insights")


def add_missing_columns() -> None:
    insp = inspect(db.engine)
    with db.engine.begin() as conn:
        for table in Base.metadata.sorted_tables:
            if not insp.has_table(table.name):
                continue
            existing = {c["name"] for c in insp.get_columns(table.name)}
            for column in table.columns:
                if column.name in existing:
                    continue
                kind = column.type.compile(dialect=db.engine.dialect)
                default = column.server_default.arg if column.server_default is not None else None
                extra = f" DEFAULT {default}" if default is not None else ""
                conn.execute(
                    text(f"ALTER TABLE {table.name} ADD COLUMN {column.name} {kind}{extra}")
                )


def init_db() -> None:
    Base.metadata.create_all(db.engine)
    add_missing_columns()
