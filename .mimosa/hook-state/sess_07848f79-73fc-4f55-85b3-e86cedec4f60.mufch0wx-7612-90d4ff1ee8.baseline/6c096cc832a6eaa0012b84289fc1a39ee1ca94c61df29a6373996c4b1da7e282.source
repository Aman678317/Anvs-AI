"""Voice Profile Database Model for Biometrics & Voice Cloning (PR-03 / PR-11)."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.base import Base

if TYPE_CHECKING:
    from .organization import Organization
    from .user import User

try:
    from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
except ImportError:
    from sqlalchemy.types import UserDefinedType

    class _FallbackVector(UserDefinedType):
        """Fallback Vector type for environments without pgvector-python."""

        def __init__(self, dim: int = 256) -> None:
            self.dim = dim

        def get_col_spec(self, **_kw: Any) -> str:
            return f"vector({self.dim})"

    Vector = _FallbackVector  # type: ignore[misc, assignment]


class VoiceProfile(Base):
    """Enrolled biometric voice embedding for speaker verification & zero-shot cloning."""

    __tablename__ = "voice_profiles"

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
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    speaker_name: Mapped[str] = mapped_column(String(100), nullable=False)
    embedding: Mapped[Any] = mapped_column(Vector(256), nullable=False)
    sample_rate: Mapped[int] = mapped_column(Integer, default=16000, nullable=False)
    duration_sec: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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
    user: Mapped["User | None"] = relationship("User")
