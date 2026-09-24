"""Unit tests for Realtime Gateway ConnectionManager and Personalized Routing."""

import json
from unittest.mock import AsyncMock

import pytest

from packages.contracts import ParticipantRole, WSServerCaptionFrame
from services.realtime_gateway.manager import ClientSession, ConnectionManager


class MockWebSocket:
    """Mock WebSocket for unit testing frame dispatch."""

    def __init__(self) -> None:
        self.sent_messages: list[str] = []
        self.closed: bool = False
        self.close_code: int | None = None

    async def send_text(self, text: str) -> None:
        if self.closed:
            raise RuntimeError("WebSocket already closed")
        self.sent_messages.append(text)

    async def close(self, code: int = 1000) -> None:
        self.closed = True
        self.close_code = code


@pytest.mark.unit
@pytest.mark.asyncio
async def test_connection_lifecycle() -> None:
    manager = ConnectionManager()
    ws = MockWebSocket()
    session = ClientSession(
        websocket=ws,
        participant_id="part-1",
        user_id="user-1",
        tenant_id="tenant-1",
        role=ParticipantRole.HOST,
        listening_language="eng",
    )

    # 1. Connect
    await manager.connect("meeting-101", "part-1", session)
    assert manager.get_participant_count("meeting-101") == 1
    retrieved = manager.get_session("meeting-101", "part-1")
    assert retrieved is not None
    assert retrieved.user_id == "user-1"
    assert retrieved.role == ParticipantRole.HOST

    # 2. Get sessions list
    sessions = manager.get_meeting_sessions("meeting-101")
    assert len(sessions) == 1
    assert sessions[0].participant_id == "part-1"

    # 3. Disconnect
    removed = await manager.disconnect("meeting-101", "part-1")
    assert removed is not None
    assert removed.participant_id == "part-1"
    assert manager.get_participant_count("meeting-101") == 0
    assert manager.get_session("meeting-101", "part-1") is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_set_listening_language() -> None:
    manager = ConnectionManager()
    ws = MockWebSocket()
    session = ClientSession(
        websocket=ws,
        participant_id="part-1",
        user_id="user-1",
        tenant_id="tenant-1",
        role=ParticipantRole.PARTICIPANT,
        listening_language="eng",
    )
    await manager.connect("meeting-101", "part-1", session)

    # Change language to Japanese
    updated = await manager.set_listening_language("meeting-101", "part-1", "jpn")
    assert updated is True
    assert session.listening_language == "jpn"

    # Non-existent participant
    failed = await manager.set_listening_language("meeting-101", "part-999", "fra")
    assert failed is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_broadcast_and_targeted_send() -> None:
    manager = ConnectionManager()
    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    session1 = ClientSession(
        websocket=ws1,
        participant_id="part-1",
        user_id="user-1",
        tenant_id="tenant-1",
        role=ParticipantRole.HOST,
        listening_language="eng",
    )
    session2 = ClientSession(
        websocket=ws2,
        participant_id="part-2",
        user_id="user-2",
        tenant_id="tenant-1",
        role=ParticipantRole.PARTICIPANT,
        listening_language="fra",
    )
    await manager.connect("meeting-101", "part-1", session1)
    await manager.connect("meeting-101", "part-2", session2)

    frame = WSServerCaptionFrame(
        source_segment_id="seg-1",
        speaker_id="part-1",
        source_language="eng",
        target_language="eng",
        text="Hello everyone",
        is_final=True,
        start_ms=0,
        end_ms=1000,
    )

    # Broadcast to all
    sent_count = await manager.broadcast_to_meeting("meeting-101", frame)
    assert sent_count == 2
    assert len(ws1.sent_messages) == 1
    assert len(ws2.sent_messages) == 1

    # Broadcast excluding sender
    sent_count_excl = await manager.broadcast_to_meeting(
        "meeting-101",
        frame,
        exclude_participant_id="part-1",
    )
    assert sent_count_excl == 1
    assert len(ws1.sent_messages) == 1  # ws1 didn't receive second
    assert len(ws2.sent_messages) == 2  # ws2 received second

    # Targeted send to part-1
    targeted_ok = await manager.send_to_participant("meeting-101", "part-1", frame)
    assert targeted_ok is True
    assert len(ws1.sent_messages) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_personalized_caption_routing() -> None:
    """Validates Personalized Subtitle Routing Invariant:

    Each client receives captions specifically tailored to their active listening_language.
    """
    manager = ConnectionManager()
    ws_eng = MockWebSocket()
    ws_jpn = MockWebSocket()
    ws_fra = MockWebSocket()

    session_eng = ClientSession(
        websocket=ws_eng,
        participant_id="part-eng",
        user_id="user-1",
        tenant_id="tenant-1",
        role=ParticipantRole.HOST,
        listening_language="eng",
    )
    session_jpn = ClientSession(
        websocket=ws_jpn,
        participant_id="part-jpn",
        user_id="user-2",
        tenant_id="tenant-1",
        role=ParticipantRole.PARTICIPANT,
        listening_language="jpn",
    )
    session_fra = ClientSession(
        websocket=ws_fra,
        participant_id="part-fra",
        user_id="user-3",
        tenant_id="tenant-1",
        role=ParticipantRole.PARTICIPANT,
        listening_language="fra",
    )

    await manager.connect("meeting-xyz", "part-eng", session_eng)
    await manager.connect("meeting-xyz", "part-jpn", session_jpn)
    await manager.connect("meeting-xyz", "part-fra", session_fra)

    orig_frame = WSServerCaptionFrame(
        source_segment_id="seg-100",
        speaker_id="part-eng",
        source_language="eng",
        target_language="eng",
        text="The quarterly report is ready.",
        is_final=True,
        start_ms=0,
        end_ms=1500,
    )
    jpn_frame = WSServerCaptionFrame(
        source_segment_id="seg-100",
        speaker_id="part-eng",
        source_language="eng",
        target_language="jpn",
        text="四半期報告書の準備が整いました。",
        is_final=True,
        start_ms=0,
        end_ms=1500,
    )

    # Route between English original and Japanese translation
    delivered = await manager.route_caption(
        meeting_id="meeting-xyz",
        source_language="eng",
        target_language="jpn",
        original_frame=orig_frame,
        translated_frame=jpn_frame,
    )

    # English and Japanese participants should receive frames;
    # French participant receives nothing yet
    assert delivered == 2
    assert len(ws_eng.sent_messages) == 1
    assert len(ws_jpn.sent_messages) == 1
    assert len(ws_fra.sent_messages) == 0

    eng_data = json.loads(ws_eng.sent_messages[0])
    assert eng_data["text"] == "The quarterly report is ready."
    assert eng_data["target_language"] == "eng"

    jpn_data = json.loads(ws_jpn.sent_messages[0])
    assert jpn_data["text"] == "四半期報告書の準備が整いました。"
    assert jpn_data["target_language"] == "jpn"

    # Now deliver a French translation frame specifically
    fra_frame = WSServerCaptionFrame(
        source_segment_id="seg-100",
        speaker_id="part-eng",
        source_language="eng",
        target_language="fra",
        text="Le rapport trimestriel est prêt.",
        is_final=True,
        start_ms=0,
        end_ms=1500,
    )
    delivered_fra = await manager.deliver_caption_event("meeting-xyz", fra_frame)
    assert delivered_fra == 1
    assert len(ws_fra.sent_messages) == 1

    fra_data = json.loads(ws_fra.sent_messages[0])
    assert fra_data["text"] == "Le rapport trimestriel est prêt."
    assert fra_data["target_language"] == "fra"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_redis_presence_tracking() -> None:
    mock_redis = AsyncMock()
    mock_redis.sadd = AsyncMock()
    mock_redis.set = AsyncMock()
    mock_redis.srem = AsyncMock()
    mock_redis.delete = AsyncMock()

    manager = ConnectionManager(redis_client=mock_redis)
    ws = MockWebSocket()
    session = ClientSession(
        websocket=ws,
        participant_id="part-redis-1",
        user_id="user-redis-1",
        tenant_id="tenant-redis-1",
        role=ParticipantRole.HOST,
    )

    # 1. Connect participant -> should SADD & set presence key
    await manager.connect("meeting-redis-1", "part-redis-1", session)
    mock_redis.sadd.assert_awaited_once_with("presence:meeting:meeting-redis-1", "part-redis-1")
    mock_redis.set.assert_awaited_once_with(
        "presence:meeting:meeting-redis-1:part-redis-1",
        "user-redis-1",
        ex=300,
    )

    # 2. Disconnect participant -> should SREM & delete presence key
    await manager.disconnect("meeting-redis-1", "part-redis-1")
    mock_redis.srem.assert_awaited_once_with("presence:meeting:meeting-redis-1", "part-redis-1")
    mock_redis.delete.assert_awaited_once_with("presence:meeting:meeting-redis-1:part-redis-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cluster_participant_count() -> None:
    mock_redis = AsyncMock()
    mock_redis.scard = AsyncMock(return_value=42)

    manager = ConnectionManager(redis_client=mock_redis)
    count = await manager.get_cluster_participant_count("meeting-distributed")
    assert count == 42
    mock_redis.scard.assert_awaited_once_with("presence:meeting:meeting-distributed")


@pytest.mark.unit
def test_stale_sessions_detection() -> None:
    manager = ConnectionManager()
    ws = MockWebSocket()
    session = ClientSession(
        websocket=ws,
        participant_id="part-stale",
        user_id="user-stale",
        tenant_id="tenant-stale",
        role=ParticipantRole.PARTICIPANT,
        last_heartbeat_at=100.0,
    )
    manager._rooms["meeting-stale"] = {"part-stale": session}

    # At current time, session is idle for > 60s
    stale_list = manager.get_stale_sessions(max_idle_sec=10.0)
    assert len(stale_list) == 1
    assert stale_list[0] == ("meeting-stale", "part-stale")
