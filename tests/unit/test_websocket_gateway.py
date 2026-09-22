"""Unit tests for Realtime WebSocket Gateway Server and Handshake Protocol."""

import json

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from packages.auth.models import AuthenticatedUser
from packages.auth.tokens import create_session_ticket
from packages.contracts import (
    ParticipantRole,
    WSClientChatMessageFrame,
    WSClientJoinFrame,
    WSClientMessageType,
    WSClientPingFrame,
    WSClientSetLanguageFrame,
    WSServerMessageType,
)
from services.realtime_gateway.manager import ConnectionManager
from services.realtime_gateway.server import create_realtime_gateway_app


@pytest.fixture
def auth_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id="usr_test_123",
        tenant_id="ten_test_456",
        email="dev@example.com",
        role=ParticipantRole.HOST,
        display_name="Test Host",
    )


@pytest.fixture
def test_client() -> tuple[TestClient, ConnectionManager]:
    manager = ConnectionManager()
    app = create_realtime_gateway_app(manager=manager)
    client = TestClient(app)
    return client, manager


@pytest.mark.unit
def test_health_check(test_client: tuple[TestClient, ConnectionManager]) -> None:
    client, _ = test_client
    response = client.get("/healthz")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "realtime-gateway"


@pytest.mark.unit
def test_successful_websocket_handshake_and_ping_pong(
    test_client: tuple[TestClient, ConnectionManager],
    auth_user: AuthenticatedUser,
) -> None:
    client, manager = test_client
    meeting_id = "meeting_test_001"
    participant_id = "part_test_001"
    valid_ticket = create_session_ticket(auth_user, meeting_id=meeting_id)

    with client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws:
        # 1. Send WSClientJoinFrame
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=valid_ticket,
            participant_id=participant_id,
        )
        ws.send_text(join_frame.model_dump_json())

        # 2. Receive initial WSServerRoomStateFrame
        room_state_raw = ws.receive_text()
        room_state = json.loads(room_state_raw)
        assert room_state["type"] == WSServerMessageType.ROOM_STATE
        assert room_state["status"] == "ACTIVE"
        assert len(room_state["participants"]) == 1
        assert room_state["participants"][0]["participant_id"] == participant_id

        # Verify session is registered in manager
        assert manager.get_participant_count(meeting_id) == 1

        # 3. Send PING frame
        ping_frame = WSClientPingFrame(
            type=WSClientMessageType.PING,
            timestamp_ms=1710000000000,
        )
        ws.send_text(ping_frame.model_dump_json())

        # 4. Receive PONG frame
        pong_raw = ws.receive_text()
        pong = json.loads(pong_raw)
        assert pong["type"] == WSServerMessageType.PONG
        assert pong["timestamp_ms"] == 1710000000000

        # 5. Send SET_LISTENING_LANGUAGE frame
        lang_frame = WSClientSetLanguageFrame(
            type=WSClientMessageType.SET_LISTENING_LANGUAGE,
            listening_language="jpn",
        )
        ws.send_text(lang_frame.model_dump_json())

        # Send synchronization PING to ensure the message loop has processed the language update
        sync_ping = WSClientPingFrame(
            type=WSClientMessageType.PING,
            timestamp_ms=1710000000001,
        )
        ws.send_text(sync_ping.model_dump_json())
        sync_pong_raw = ws.receive_text()
        sync_pong = json.loads(sync_pong_raw)
        assert sync_pong["type"] == WSServerMessageType.PONG
        assert sync_pong["timestamp_ms"] == 1710000000001

        # Verify manager updated language
        session = manager.get_session(meeting_id, participant_id)
        assert session is not None
        assert session.listening_language == "jpn"

    # After websocket context exit, participant should be disconnected
    assert manager.get_participant_count(meeting_id) == 0


@pytest.mark.unit
def test_websocket_rejects_expired_ticket(
    test_client: tuple[TestClient, ConnectionManager],
    auth_user: AuthenticatedUser,
) -> None:
    client, _ = test_client
    meeting_id = "meeting_test_002"
    expired_ticket = create_session_ticket(auth_user, meeting_id=meeting_id, ttl_seconds=-10)

    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws,
    ):
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=expired_ticket,
            participant_id="part_test_002",
        )
        ws.send_text(join_frame.model_dump_json())
        err_raw = ws.receive_text()
        err = json.loads(err_raw)
        assert err["type"] == WSServerMessageType.ERROR
        assert err["code"] == "AUTH_EXPIRED"
        # The connection will now close
        ws.receive_text()

    assert exc_info.value.code == 1008


@pytest.mark.unit
def test_websocket_rejects_mismatched_meeting_id(
    test_client: tuple[TestClient, ConnectionManager],
    auth_user: AuthenticatedUser,
) -> None:
    client, _ = test_client
    meeting_id = "meeting_test_correct"
    wrong_meeting_ticket = create_session_ticket(auth_user, meeting_id="meeting_test_different")

    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws,
    ):
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=wrong_meeting_ticket,
            participant_id="part_test_003",
        )
        ws.send_text(join_frame.model_dump_json())
        err_raw = ws.receive_text()
        err = json.loads(err_raw)
        assert err["type"] == WSServerMessageType.ERROR
        assert err["code"] == "FORBIDDEN_ROOM"
        ws.receive_text()

    assert exc_info.value.code == 1008


@pytest.mark.unit
def test_websocket_rejects_invalid_first_frame(
    test_client: tuple[TestClient, ConnectionManager],
) -> None:
    client, _ = test_client
    meeting_id = "meeting_test_004"

    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws,
    ):
        # Send PING before JOIN
        ping_frame = WSClientPingFrame(
            type=WSClientMessageType.PING,
            timestamp_ms=12345,
        )
        ws.send_text(ping_frame.model_dump_json())
        err_raw = ws.receive_text()
        err = json.loads(err_raw)
        assert err["type"] == WSServerMessageType.ERROR
        assert err["code"] == "INVALID_JOIN_FRAME"
        ws.receive_text()

    assert exc_info.value.code == 1008


@pytest.mark.unit
def test_websocket_rate_limiting(
    test_client: tuple[TestClient, ConnectionManager],
    auth_user: AuthenticatedUser,
) -> None:
    client, _ = test_client
    meeting_id = "meeting_test_rate_limit"
    valid_ticket = create_session_ticket(auth_user, meeting_id=meeting_id)

    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws,
    ):
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=valid_ticket,
            participant_id="part_rate_limit",
        )
        ws.send_text(join_frame.model_dump_json())
        ws.receive_text()  # Room state

        # Exceed rate limit (> 50 messages)
        ping_frame = WSClientPingFrame(
            type=WSClientMessageType.PING,
            timestamp_ms=1000,
        )
        ping_json = ping_frame.model_dump_json()

        for _ in range(55):
            ws.send_text(ping_json)

        # One of the responses should be RATE_LIMIT_EXCEEDED
        found_rate_limit_error = False
        while True:
            raw = ws.receive_text()
            data = json.loads(raw)
            if data.get("code") == "RATE_LIMIT_EXCEEDED":
                found_rate_limit_error = True
                break

        assert found_rate_limit_error is True
        ws.receive_text()

    assert exc_info.value.code == 1008


@pytest.mark.unit
def test_websocket_chat_message_broadcast(
    test_client: tuple[TestClient, ConnectionManager],
    auth_user: AuthenticatedUser,
) -> None:
    client, _ = test_client
    meeting_id = "meeting_test_chat"
    valid_ticket = create_session_ticket(auth_user, meeting_id=meeting_id)

    with client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws:
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=valid_ticket,
            participant_id="part_chat_user",
        )
        ws.send_text(join_frame.model_dump_json())
        ws.receive_text()  # Room state

        # Send chat message
        chat_frame = WSClientChatMessageFrame(
            type=WSClientMessageType.CHAT_MESSAGE,
            text="Hello real-time team!",
        )
        ws.send_text(chat_frame.model_dump_json())

        # Receive broadcast caption update
        msg_raw = ws.receive_text()
        msg = json.loads(msg_raw)
        assert msg["type"] == WSServerMessageType.CAPTION_UPDATE
        assert "Hello real-time team!" in msg["text"]
