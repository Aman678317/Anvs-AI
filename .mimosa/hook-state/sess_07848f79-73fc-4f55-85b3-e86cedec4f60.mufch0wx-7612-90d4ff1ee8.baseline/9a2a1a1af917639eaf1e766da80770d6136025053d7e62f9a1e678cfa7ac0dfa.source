"""Database Engine, Session Management & RLS Tenant Context Injection."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from packages.config.settings import settings

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_async_engine(database_url: str | None = None) -> AsyncEngine:
    """Create or return existing cached asynchronous SQLAlchemy engine."""
    global _engine
    if _engine is None:
        target_url = database_url or settings.database_url
        if target_url.startswith("postgresql://"):
            target_url = "postgresql+asyncpg://" + target_url[len("postgresql://") :]

        engine_kwargs: dict[str, Any] = {
            "echo": settings.debug,
            "future": True,
        }
        # Connection pooling parameters for PostgreSQL (asyncpg)
        if "postgresql" in target_url:
            is_pgbouncer = (
                "pgbouncer=true" in target_url
                or ":6543" in target_url
                or "pooler.supabase.com" in target_url
            )
            # Remove pgbouncer query parameter so asyncpg.connect does not raise unexpected kwarg
            clean_url = (
                target_url.replace("?pgbouncer=true&", "?")
                .replace("&pgbouncer=true", "")
                .replace("?pgbouncer=true", "")
            )
            connect_args: dict[str, Any] = {}
            if is_pgbouncer:
                connect_args["statement_cache_size"] = 0

            engine_kwargs.update(
                {
                    "pool_size": 20,
                    "max_overflow": 10,
                    "pool_pre_ping": True,
                }
            )
            if connect_args:
                engine_kwargs["connect_args"] = connect_args
            target_url = clean_url

        _engine = create_async_engine(target_url, **engine_kwargs)
    return _engine


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Create or return existing cached async sessionmaker."""
    global _sessionmaker
    if _sessionmaker is None:
        target_engine = engine or get_async_engine()
        _sessionmaker = async_sessionmaker(
            bind=target_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )
    return _sessionmaker


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional asynchronous database session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def get_tenant_session(
    tenant_id: str,
    database_url: str | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a tenant-scoped session enforcing PostgreSQL Row Level Security (RLS).

    Executes SET LOCAL app.current_tenant_id = :tenant_id within the transaction
    so that PostgreSQL RLS policies mathematically restrict visible rows.
    """
    factory = get_session_factory(get_async_engine(database_url))
    async with factory() as session, session.begin():
        # Inject tenant context for PostgreSQL RLS policy evaluation
        await session.execute(
            text("SET LOCAL app.current_tenant_id = :tenant_id"),
            {"tenant_id": str(tenant_id)},
        )
        yield session


async def get_db_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI route dependency yielding a transactional AsyncSession."""
    async with get_db_session() as session:
        yield session
