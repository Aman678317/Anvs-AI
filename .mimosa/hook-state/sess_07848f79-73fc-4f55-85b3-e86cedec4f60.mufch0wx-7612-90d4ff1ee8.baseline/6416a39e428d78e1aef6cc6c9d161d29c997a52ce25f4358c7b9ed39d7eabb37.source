"""Meeting Settings Database Model (PR-03)."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.base import Base

if TYPE_CHECKING:
    from .meeting import Meeting
    from .organization import Organization


class MeetingSetting(Base):
    """Per-meeting governance, audio, transcription, and security settings."""

    __tablename__ = "meeting_settings"

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
        unique=True,
        index=True,
    )
    enable_recording: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enable_transcription: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_translation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_voice_cloning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retention_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    allowed_languages: Mapped[list[str]] = mapped_column(
        JSON,
        default=lambda: ["eng", "spa", "fra", "deu", "hin", "jpn"],
        nullable=False,
    )
    extra_features: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    organization: Mapped["Organization"] = relationship("Organization")
    meeting: Mapped["Meeting"] = relationship("Meeting")
