"""Unit tests for Database Engine, Session Factory, and RLS Context Injection."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from packages.database.seed import (
    DEFAULT_TENANT_ID,
    SECONDARY_TENANT_ID,
    seed_database,
)
from packages.database.session import (
    get_async_engine,
    get_session_factory,
    get_tenant_session,
)


@pytest.mark.unit
def test_engine_and_sessionmaker_caching() -> None:
    engine1 = get_async_engine("sqlite+aiosqlite:///:memory:")
    engine2 = get_async_engine()
    assert engine1 is engine2

    factory = get_session_factory(engine1)
    assert factory is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tenant_session_rls_injection() -> None:
    test_tenant_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session.begin.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)

    mock_factory = MagicMock()
    mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
    mock_factory.return_value.__aexit__ = AsyncMock(return_value=None)

    with patch(
        "packages.database.session.get_session_factory",
        return_value=mock_factory,
    ):
        async with get_tenant_session(test_tenant_id) as session:
            assert session is mock_session

    # Verify that SET LOCAL app.current_tenant_id was executed with test_tenant_id
    mock_session.execute.assert_awaited_once()
    call_args = mock_session.execute.call_args
    sql_text = str(call_args.args[0])
    assert "SET LOCAL app.current_tenant_id = :tenant_id" in sql_text
    assert call_args.args[1] == {"tenant_id": test_tenant_id}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_seed_database_execution() -> None:
    mock_session = AsyncMock()
    # Mock scalar_one_or_none to return None for each query, triggering object creation
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_result

    seed_result = await seed_database(mock_session)

    assert seed_result["tenant_id"] == str(DEFAULT_TENANT_ID)
    assert seed_result["secondary_tenant_id"] == str(SECONDARY_TENANT_ID)
    assert mock_session.add.call_count == 5
    mock_session.commit.assert_awaited_once()
