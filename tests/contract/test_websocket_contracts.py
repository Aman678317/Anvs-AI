"""Tests for WebSocket Frame Contracts."""

import pytest
from pydantic import ValidationError

from packages.contracts import (
    AudioStreamType,
    MeetingStatus,
    ParticipantContract,
    ParticipantRole,
    WSClientChatMessageFrame,
    WSClientJoinFrame,
    WSClientMessageType,
    WSClientPingFrame,
    WSClientQueryAssistantFrame,
    WSClientSetLanguageFrame,
    WSServerAssistantFrame,
    WSServerAudioTrackFrame,
    WSServerCaptionFrame,
    WSServerErrorFrame,
    WSServerMessageType,
    WSServerParticipantJoinedFrame,
    WSServerParticipantLeftFrame,
    WSServerPongFrame,
    WSServerRoomStateFrame,
)


@pytest.mark.contract
def test_client_join_and_set_language_frames() -> None:
    join_frame = WSClientJoinFrame(
        ticket="ws-ticket-abc",
        participant_id="part-123",
    )
    assert join_frame.type == WSClientMessageType.JOIN
    assert join_frame.ticket == "ws-ticket-abc"

    lang_frame = WSClientSetLanguageFrame(listening_language="jpn")
    assert lang_frame.type == WSClientMessageType.SET_LISTENING_LANGUAGE
    assert lang_frame.listening_language == "jpn"

    # Invalid language length
    with pytest.raises(ValidationError):
        WSClientSetLanguageFrame(listening_language="japanese")


@pytest.mark.contract
def test_server_caption_frame_lineage() -> None:
    caption_frame = WSServerCaptionFrame(
        source_segment_id="src-seg-100",
        speaker_id="spk-2",
        source_language="spa",
        target_language="eng",
        text="All systems operational.",
        is_final=False,
        start_ms=500,
        end_ms=1200,
    )
    assert caption_frame.type == WSServerMessageType.CAPTION_UPDATE
    assert caption_frame.source_segment_id == "src-seg-100"
    assert caption_frame.is_final is False


@pytest.mark.contract
def test_server_audio_track_frame() -> None:
    track_frame = WSServerAudioTrackFrame(
        track_sid="TR_12345",
        language="spa",
        stream_type=AudioStreamType.TRANSLATED_SYNTHETIC,
    )
    assert track_frame.type == WSServerMessageType.AUDIO_TRACK_PUBLISHED
    assert track_frame.stream_type == AudioStreamType.TRANSLATED_SYNTHETIC


@pytest.mark.contract
def test_server_error_frame_serialization() -> None:
    err_frame = WSServerErrorFrame(
        code="UNAUTHORIZED_ROOM_ACCESS",
        message="Session ticket has expired.",
    )
    assert err_frame.type == WSServerMessageType.ERROR

    json_str = err_frame.model_dump_json()
    reparsed = WSServerErrorFrame.model_validate_json(json_str)
    assert reparsed.code == "UNAUTHORIZED_ROOM_ACCESS"
