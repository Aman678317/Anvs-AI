"""System Health & Deep Dependency Readiness Probes Router."""

import logging
import time
from typing import Any

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from packages.config.settings import settings
from packages.database.session import get_session_factory
from packages.event_schema.bus import RedisStreamBus

logger = logging.getLogger(__name__)

router = APIRouter(tags=["System"])

_START_TIME = time.time()


@router.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    summary="Liveness probe for process uptime and basic responsiveness",
)
async def liveness_probe() -> dict[str, Any]:
    """Lightweight liveness probe checking process responsiveness."""
    return {
        "status": "healthy",
        "service": "api-control-plane",
        "version": "1.0.0",
        "environment": settings.app_env,
        "uptime_seconds": round(time.time() - _START_TIME, 2),
    }


@router.get(
    "/readyz",
    summary="Deep readiness probe checking database and redis connectivity",
)
async def readiness_probe(response: Response) -> dict[str, Any]:
    """Deep readiness probe verifying PostgreSQL and Redis connections."""
    checks: dict[str, str] = {
        "database": "unknown",
        "redis": "unknown",
    }
    is_ready = True

    # 1. Check PostgreSQL Database Connectivity
    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1;"))
            if result.scalar() == 1:
                checks["database"] = "healthy"
            else:
                checks["database"] = "unexpected_response"
                is_ready = False
    except Exception as exc:
        logger.error("Readiness check failed for PostgreSQL: %s", exc)
        checks["database"] = f"unhealthy: {exc.__class__.__name__}"
        is_ready = False

    # 2. Check Redis Event Plane Connectivity
    try:
        bus = RedisStreamBus()
        client = await bus.connect()
        ping_ok = await client.ping()
        if ping_ok:
            checks["redis"] = "healthy"
        else:
            checks["redis"] = "ping_failed"
            is_ready = False
        await bus.disconnect()
    except Exception as exc:
        logger.error("Readiness check failed for Redis: %s", exc)
        checks["redis"] = f"unhealthy: {exc.__class__.__name__}"
        is_ready = False

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "degraded",
            "service": "api-control-plane",
            "checks": checks,
        }

    response.status_code = status.HTTP_200_OK
    return {
        "status": "ready",
        "service": "api-control-plane",
        "checks": checks,
    }
