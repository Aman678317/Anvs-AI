"""Transcript Segment Database Model (Invariant #2: Source Lineage)."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.base import Base

if TYPE_CHECKING:
    from .embedding import TranscriptEmbedding
    from .meeting import Meeting


class TranscriptSegment(Base):
    """Lineaged speech and translated transcript record."""

    __tablename__ = "transcript_segments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_segment_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        doc="Immutable lineage root identifier",
    )
    speaker_id: Mapped[str] = mapped_column(String(100), nullable=False)
    speaker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    source_language: Mapped[str] = mapped_column(String(3), nullable=False)
    target_language: Mapped[str] = mapped_column(String(3), nullable=False)
    original_text: Mapped[str] = mapped_column(Text, nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    is_final: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(
        "Meeting",
        back_populates="transcript_segments",
    )
    embedding: Mapped["TranscriptEmbedding | None"] = relationship(
        "TranscriptEmbedding",
        back_populates="segment",
        cascade="all, delete-orphan",
        uselist=False,
    )
