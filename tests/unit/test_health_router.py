"""Unit tests for /healthz and /readyz probes (PR-01)."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from services.api.routers.health import router as health_router

app = FastAPI()
app.include_router(health_router)
client = TestClient(app)


@pytest.mark.unit
def test_liveness_probe() -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "api-control-plane"
    assert data["version"] == "1.0.0"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0


@pytest.mark.unit
def test_readiness_probe_healthy() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with (
        patch("services.api.routers.health.get_session_factory", return_value=mock_factory),
        patch("services.api.routers.health.RedisStreamBus") as mock_bus_cls,
    ):
        mock_bus_inst = AsyncMock()
        mock_bus_inst.connect = AsyncMock(return_value=mock_redis)
        mock_bus_inst.disconnect = AsyncMock()
        mock_bus_cls.return_value = mock_bus_inst

        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["checks"]["database"] == "healthy"
        assert data["checks"]["redis"] == "healthy"


@pytest.mark.unit
def test_readiness_probe_db_failure() -> None:
    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(side_effect=ConnectionRefusedError("DB offline"))
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_redis = AsyncMock()
    mock_redis.ping = AsyncMock(return_value=True)

    with (
        patch("services.api.routers.health.get_session_factory", return_value=mock_factory),
        patch("services.api.routers.health.RedisStreamBus") as mock_bus_cls,
    ):
        mock_bus_inst = AsyncMock()
        mock_bus_inst.connect = AsyncMock(return_value=mock_redis)
        mock_bus_inst.disconnect = AsyncMock()
        mock_bus_cls.return_value = mock_bus_inst

        response = client.get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert "unhealthy" in data["checks"]["database"]
        assert data["checks"]["redis"] == "healthy"


@pytest.mark.unit
def test_readiness_probe_redis_failure() -> None:
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 1
    mock_session.execute = AsyncMock(return_value=mock_result)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    with (
        patch("services.api.routers.health.get_session_factory", return_value=mock_factory),
        patch("services.api.routers.health.RedisStreamBus") as mock_bus_cls,
    ):
        mock_bus_inst = AsyncMock()
        mock_bus_inst.connect = AsyncMock(side_effect=TimeoutError("Redis timed out"))
        mock_bus_cls.return_value = mock_bus_inst

        response = client.get("/readyz")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "degraded"
        assert data["checks"]["database"] == "healthy"
        assert "unhealthy" in data["checks"]["redis"]
