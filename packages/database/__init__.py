"""Database Package for the Multilingual AI Meeting Platform."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .base import Base
from .models import (
    IdempotencyKey,
    Meeting,
    MeetingChatMessage,
    MeetingSetting,
    Organization,
    OrganizationMember,
    OutboxEvent,
    Participant,
    SourceSegment,
    TranscriptEmbedding,
    TranscriptSegment,
    User,
    UserSession,
    VoiceProfile,
)
from .seed import seed_database
from .session import (
    get_async_engine,
    get_db_session,
    get_db_session_dependency,
    get_session_factory,
    get_tenant_session,
)

__all__ = [
    "AsyncSession",
    "Base",
    "IdempotencyKey",
    "Meeting",
    "MeetingChatMessage",
    "MeetingSetting",
    "Organization",
    "OrganizationMember",
    "OutboxEvent",
    "Participant",
    "SourceSegment",
    "TranscriptEmbedding",
    "TranscriptSegment",
    "User",
    "UserSession",
    "VoiceProfile",
    "async_sessionmaker",
    "create_async_engine",
    "get_async_engine",
    "get_db_session",
    "get_db_session_dependency",
    "get_session_factory",
    "get_tenant_session",
    "seed_database",
]
