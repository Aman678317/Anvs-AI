"""User Database Model."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.database.base import Base

if TYPE_CHECKING:
    from .meeting import Meeting
    from .organization import Organization
    from .participant import Participant


class User(Base):
    """Tenant-scoped user model."""

    __tablename__ = "users"

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
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(50), default="PARTICIPANT", nullable=False)
    default_spoken_language: Mapped[str] = mapped_column(String(3), default="eng", nullable=False)
    default_listening_language: Mapped[str] = mapped_column(
        String(3), default="eng", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
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

    # Relationships
    organization: Mapped["Organization"] = relationship(
        "Organization",
        back_populates="users",
    )
    meetings_created: Mapped[list["Meeting"]] = relationship(
        "Meeting",
        back_populates="creator",
    )
    participants: Mapped[list["Participant"]] = relationship(
        "Participant",
        back_populates="user",
    )
