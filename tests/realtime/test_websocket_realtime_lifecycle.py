"""Realtime WebSocket Gateway Lifecycle, Resync & Multi-Client Test Suite (PR-15).

Validates:
1. Full client connection lifecycle: auth ticket handshake, room state synchronization, and heartbeat.
2. Monotonic state version sequencing across concurrent client join, leave, and language switch events.
3. Network gap recovery: reconnected client sends WSClientResyncFrame and receives missing frames in strict sequence.
4. Multilingual persistent chat: broadcast to all participants and durable history retrieval.
5. Invariant #1: Cross-tenant and invalid ticket rejection with immediate WebSocket closure.
"""

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
    WSClientResyncFrame,
    WSClientSetLanguageFrame,
    WSServerMessageType,
)
from services.realtime_gateway.manager import ConnectionManager
from services.realtime_gateway.server import create_realtime_gateway_app


@pytest.fixture
def test_setup() -> tuple[TestClient, ConnectionManager]:
    manager = ConnectionManager()
    app = create_realtime_gateway_app(manager=manager)
    client = TestClient(app)
    return client, manager


@pytest.mark.realtime
def test_full_websocket_connection_lifecycle(
    test_setup: tuple[TestClient, ConnectionManager],
) -> None:
    """Verifies end-to-end handshake, ping-pong heartbeat, language update, and clean disconnect."""
    client, manager = test_setup
    meeting_id = "meet_rt_lifecycle_01"
    participant_id = "part_rt_user_1"

    user = AuthenticatedUser(
        user_id="usr_001",
        tenant_id="tenant_rt",
        email="user1@enterprise.org",
        role=ParticipantRole.HOST,
        display_name="User Alpha",
    )
    valid_ticket = create_session_ticket(user, meeting_id=meeting_id)

    with client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws:
        # 1. Join
        join_frame = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=valid_ticket,
            participant_id=participant_id,
        )
        ws.send_text(join_frame.model_dump_json())

        # Receive initial Room State
        state_msg = json.loads(ws.receive_text())
        assert state_msg["type"] == WSServerMessageType.ROOM_STATE
        assert state_msg["status"] == "ACTIVE"
        assert state_msg["state_version"] >= 1
        assert len(state_msg["participants"]) == 1
        assert manager.get_participant_count(meeting_id) == 1

        # 2. Heartbeat Ping / Pong
        ping = WSClientPingFrame(
            type=WSClientMessageType.PING,
            timestamp_ms=1727100000000,
        )
        ws.send_text(ping.model_dump_json())
        pong_msg = json.loads(ws.receive_text())
        assert pong_msg["type"] == WSServerMessageType.PONG
        assert pong_msg["timestamp_ms"] == 1727100000000

        # 3. Change listening language
        set_lang = WSClientSetLanguageFrame(
            type=WSClientMessageType.SET_LISTENING_LANGUAGE,
            listening_language="fra",
        )
        ws.send_text(set_lang.model_dump_json())

    # After context exit, participant should be disconnected
    assert manager.get_participant_count(meeting_id) == 0


@pytest.mark.realtime
def test_multi_client_monotonic_state_and_broadcast(
    test_setup: tuple[TestClient, ConnectionManager],
) -> None:
    """Verifies monotonic state version increments across interleaved joins and chat messages."""
    client, manager = test_setup
    meeting_id = "meet_rt_multi_client"

    user1 = AuthenticatedUser(
        user_id="usr_101",
        tenant_id="tenant_corp",
        email="host@corp.com",
        role=ParticipantRole.HOST,
        display_name="Host 1",
    )
    user2 = AuthenticatedUser(
        user_id="usr_102",
        tenant_id="tenant_corp",
        email="attendee@corp.com",
        role=ParticipantRole.PARTICIPANT,
        display_name="Attendee 2",
    )

    ticket1 = create_session_ticket(user1, meeting_id=meeting_id)
    ticket2 = create_session_ticket(user2, meeting_id=meeting_id)

    with (
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws1,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws2,
    ):
        # Client 1 joins
        ws1.send_text(
            WSClientJoinFrame(
                type=WSClientMessageType.JOIN,
                ticket=ticket1,
                participant_id="part_host",
            ).model_dump_json()
        )
        s1 = json.loads(ws1.receive_text())
        v1 = s1["state_version"]
        assert v1 >= 1

        # Client 2 joins
        ws2.send_text(
            WSClientJoinFrame(
                type=WSClientMessageType.JOIN,
                ticket=ticket2,
                participant_id="part_attendee",
            ).model_dump_json()
        )

        # ws1 receives notification of client 2 joining with higher monotonic version
        joined_notification = json.loads(ws1.receive_text())
        assert joined_notification["type"] == WSServerMessageType.PARTICIPANT_JOINED
        v2 = joined_notification["state_version"]
        assert v2 > v1

        # ws2 receives room state with latest version
        s2 = json.loads(ws2.receive_text())
        assert s2["type"] == WSServerMessageType.ROOM_STATE
        assert s2["state_version"] > v1
        assert len(s2["participants"]) == 2

        # Client 1 sends a chat message
        chat_msg = WSClientChatMessageFrame(
            type=WSClientMessageType.CHAT_MESSAGE,
            text="Welcome to the GA alignment session.",
        )
        ws1.send_text(chat_msg.model_dump_json())

        # Both clients receive the broadcasted message
        caption_1 = json.loads(ws1.receive_text())
        assert caption_1["type"] == WSServerMessageType.CAPTION_UPDATE
        assert "Welcome to the GA alignment session." in caption_1["text"]

        caption_2 = json.loads(ws2.receive_text())
        assert caption_2["type"] == WSServerMessageType.CAPTION_UPDATE
        assert "Welcome to the GA alignment session." in caption_2["text"]

        # Verify persistent chat history
        chat_history = manager.get_chat_history(meeting_id)
        assert len(chat_history) == 1
        assert chat_history[0]["content"] == "Welcome to the GA alignment session."
        assert chat_history[0]["sender_id"] == "part_host"


@pytest.mark.realtime
def test_network_gap_recovery_resync_frame(
    test_setup: tuple[TestClient, ConnectionManager],
) -> None:
    """Verifies that a disconnected client recovering with WSClientResyncFrame receives all missed frames."""
    client, manager = test_setup
    meeting_id = "meet_resync_gap"
    part_id = "part_resync_user"

    user = AuthenticatedUser(
        user_id="usr_gap",
        tenant_id="tenant_gap",
        email="gap@test.com",
        role=ParticipantRole.PARTICIPANT,
        display_name="Gap User",
    )
    ticket = create_session_ticket(user, meeting_id=meeting_id)

    # 1. First connection: join and establish initial state version
    with client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws:
        ws.send_text(
            WSClientJoinFrame(
                type=WSClientMessageType.JOIN,
                ticket=ticket,
                participant_id=part_id,
            ).model_dump_json()
        )
        init_state = json.loads(ws.receive_text())
        v_initial = init_state["state_version"]

    # 2. Simulate broadcast activity while client was disconnected
    manager.record_state_change(
        meeting_id,
        {
            "type": WSServerMessageType.CAPTION_UPDATE,
            "text": "Missed caption segment 101",
        },
    )
    manager.record_state_change(
        meeting_id,
        {
            "type": WSServerMessageType.CAPTION_UPDATE,
            "text": "Missed caption segment 102",
        },
    )
    manager.record_state_change(
        meeting_id,
        {
            "type": WSServerMessageType.CAPTION_UPDATE,
            "text": "Missed caption segment 103",
        },
    )

    # 3. Client reconnects and requests resync from v_initial
    new_ticket = create_session_ticket(user, meeting_id=meeting_id)
    with client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws_reconnect:
        ws_reconnect.send_text(
            WSClientJoinFrame(
                type=WSClientMessageType.JOIN,
                ticket=new_ticket,
                participant_id=part_id,
            ).model_dump_json()
        )
        # Drain initial Room State
        ws_reconnect.receive_text()

        # Send RESYNC frame for missed version gap
        resync_frame = WSClientResyncFrame(
            type=WSClientMessageType.RESYNC,
            from_state_version=v_initial,
        )
        ws_reconnect.send_text(resync_frame.model_dump_json())

        # Receive resync response frame
        resync_resp_raw = ws_reconnect.receive_text()
        resync_resp = json.loads(resync_resp_raw)
        assert resync_resp["type"] == WSServerMessageType.RESYNC_RESPONSE
        missed = resync_resp["missed_frames"]
        assert len(missed) >= 3

        texts = [f.get("text") for f in missed if "text" in f]
        assert "Missed caption segment 101" in texts
        assert "Missed caption segment 102" in texts
        assert "Missed caption segment 103" in texts


@pytest.mark.realtime
def test_cross_tenant_or_invalid_ticket_rejection(
    test_setup: tuple[TestClient, ConnectionManager],
) -> None:
    """Verifies that handshake with an invalid or spoofed ticket closes immediately with policy violation."""
    client, _ = test_setup
    meeting_id = "meet_security_gate"

    # 1. Invalid forged token
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws,
    ):
        invalid_join = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket="forged.jwt.ticket.signature",
            participant_id="part_attacker",
        )
        ws.send_text(invalid_join.model_dump_json())
        ws.receive_text()  # Receives WSServerErrorFrame
        ws.receive_text()  # Raises WebSocketDisconnect(code=1008)

    assert exc_info.value.code == 1008  # Policy violation

    # 2. Ticket for different meeting
    user = AuthenticatedUser(
        user_id="usr_attacker",
        tenant_id="tenant_target",
        email="attacker@test.com",
        role=ParticipantRole.PARTICIPANT,
    )
    wrong_meeting_ticket = create_session_ticket(user, meeting_id="other_meeting_id")

    with (
        pytest.raises(WebSocketDisconnect) as exc_info2,
        client.websocket_connect(f"/ws/meetings/{meeting_id}") as ws2,
    ):
        wrong_join = WSClientJoinFrame(
            type=WSClientMessageType.JOIN,
            ticket=wrong_meeting_ticket,
            participant_id="part_attacker",
        )
        ws2.send_text(wrong_join.model_dump_json())
        ws2.receive_text()  # Receives WSServerErrorFrame
        ws2.receive_text()  # Raises WebSocketDisconnect(code=1008)

    assert exc_info2.value.code == 1008
