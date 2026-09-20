"""Contract tests for WebSocket Gateway Inbound and Outbound Frames."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from packages.contracts import (
    MeetingStatus,
    ParticipantContract,
    ParticipantRole,
    WSClientChatMessageFrame,
    WSClientMessageType,
    WSClientPingFrame,
    WSClientQueryAssistantFrame,
    WSServerAssistantFrame,
    WSServerMessageType,
    WSServerParticipantJoinedFrame,
    WSServerParticipantLeftFrame,
    WSServerPongFrame,
    WSServerRoomStateFrame,
)


@pytest.mark.contract
def test_client_chat_and_assistant_frames() -> None:
    chat_frame = WSClientChatMessageFrame(text="Hello from the chat client")
    assert chat_frame.type == WSClientMessageType.CHAT_MESSAGE
    assert chat_frame.text == "Hello from the chat client"

    # Chat empty string rejection
    with pytest.raises(ValidationError):
        WSClientChatMessageFrame(text="")

    asst_frame = WSClientQueryAssistantFrame(
        query_id="query_contract_01",
        question="What was decided about the deployment date?",
    )
    assert asst_frame.type == WSClientMessageType.QUERY_ASSISTANT
    assert asst_frame.query_id == "query_contract_01"

    ping_frame = WSClientPingFrame(timestamp_ms=1710000000000)
    assert ping_frame.type == WSClientMessageType.PING
    assert ping_frame.timestamp_ms == 1710000000000


@pytest.mark.contract
def test_server_room_state_and_presence_frames() -> None:
    now = datetime.now(UTC)
    participant = ParticipantContract(
        participant_id="part_contract_1",
        user_id="user_contract_1",
        display_name="Auditor",
        role=ParticipantRole.MODERATOR,
        spoken_language="deu",
        listening_language="eng",
        is_muted=False,
        is_video_enabled=True,
        joined_at=now,
    )

    state_frame = WSServerRoomStateFrame(
        state_version=3,
        status=MeetingStatus.ACTIVE,
        participants=[participant],
    )
    assert state_frame.type == WSServerMessageType.ROOM_STATE
    assert state_frame.state_version == 3
    assert len(state_frame.participants) == 1
    assert state_frame.participants[0].role == ParticipantRole.MODERATOR

    # Serialization roundtrip
    json_str = state_frame.model_dump_json()
    reparsed = WSServerRoomStateFrame.model_validate_json(json_str)
    assert reparsed.participants[0].participant_id == "part_contract_1"

    # Participant joined frame
    joined_frame = WSServerParticipantJoinedFrame(
        state_version=4,
        participant=participant,
    )
    assert joined_frame.type == WSServerMessageType.PARTICIPANT_JOINED
    assert joined_frame.participant.display_name == "Auditor"

    # Participant left frame
    left_frame = WSServerParticipantLeftFrame(
        state_version=5,
        participant_id="part_contract_1",
    )
    assert left_frame.type == WSServerMessageType.PARTICIPANT_LEFT
    assert left_frame.participant_id == "part_contract_1"


@pytest.mark.contract
def test_server_assistant_and_pong_frames() -> None:
    asst_resp = WSServerAssistantFrame(
        query_id="query_contract_01",
        answer="The deployment is scheduled for next Monday.",
        citations=["seg-1", "seg-2"],
        action_items=["Bob to verify staging by Friday"],
    )
    assert asst_resp.type == WSServerMessageType.ASSISTANT_RESPONSE
    assert len(asst_resp.citations) == 2
    assert len(asst_resp.action_items) == 1

    pong = WSServerPongFrame(timestamp_ms=1710000000000)
    assert pong.type == WSServerMessageType.PONG
    assert pong.timestamp_ms == 1710000000000
