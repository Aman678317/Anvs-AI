"""Unit tests for LiveKit WebRTC Service."""

import base64
import hashlib
import json

import pytest
from jose import jwt

from packages.contracts import ParticipantRole
from services.api.services.livekit_service import LiveKitService


@pytest.fixture
def livekit_svc() -> LiveKitService:
    return LiveKitService(
        url="ws://localhost:7880",
        api_key="test_api_key",
        api_secret="test_api_secret_key_32_characters_minimum",
    )


@pytest.mark.unit
def test_generate_token_for_host(livekit_svc: LiveKitService) -> None:
    token = livekit_svc.generate_token(
        room_name="room_123",
        identity="part_host_1",
        name="Sarah Host",
        role=ParticipantRole.HOST,
        metadata={"tenant_id": "tenant_1", "spoken_language": "eng"},
    )
    assert isinstance(token, str)

    # Decode and verify LiveKit claims
    claims = jwt.decode(
        token,
        livekit_svc.api_secret,
        algorithms=["HS256"],
        options={"verify_signature": True},
    )
    assert claims["iss"] == "test_api_key"
    assert claims["sub"] == "part_host_1"
    assert claims["name"] == "Sarah Host"
    assert claims["video"]["room"] == "room_123"
    assert claims["video"]["roomJoin"] is True
    assert claims["video"]["canPublish"] is True
    assert claims["video"]["canSubscribe"] is True
    assert claims["video"]["canPublishData"] is True

    # Verify embedded metadata
    meta = json.loads(claims["metadata"])
    assert meta["tenant_id"] == "tenant_1"
    assert meta["spoken_language"] == "eng"
    assert meta["role"] == "HOST"


@pytest.mark.unit
def test_generate_token_for_guest(livekit_svc: LiveKitService) -> None:
    token = livekit_svc.generate_token(
        room_name="room_123",
        identity="part_guest_1",
        name="John Guest",
        role=ParticipantRole.GUEST,
        metadata={"tenant_id": "tenant_1"},
    )
    claims = jwt.decode(
        token,
        livekit_svc.api_secret,
        algorithms=["HS256"],
        options={"verify_signature": True},
    )
    # Guest cannot publish media or send data
    assert claims["video"]["canPublish"] is False
    assert claims["video"]["canPublishData"] is False
    assert claims["video"]["canSubscribe"] is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_room_lifecycle_provisioning(livekit_svc: LiveKitService) -> None:
    desc = await livekit_svc.create_room("room_test_lifecycle")
    assert desc["name"] == "room_test_lifecycle"
    assert desc["status"] == "ACTIVE"

    teardown_result = await livekit_svc.delete_room("room_test_lifecycle")
    assert teardown_result is True


@pytest.mark.unit
def test_verify_webhook_valid_signature(livekit_svc: LiveKitService) -> None:
    event_payload = {
        "event": "participant_joined",
        "room": {"name": "room_123"},
        "participant": {"identity": "part_1", "name": "Alex"},
    }
    raw_body = json.dumps(event_payload).encode("utf-8")
    computed_sha = base64.b64encode(hashlib.sha256(raw_body).digest()).decode("utf-8")

    auth_token = jwt.encode(
        {"sha256": computed_sha},
        livekit_svc.api_secret,
        algorithm="HS256",
    )

    parsed = livekit_svc.verify_webhook(raw_body, auth_token)
    assert parsed["event"] == "participant_joined"
    assert parsed["room"]["name"] == "room_123"

    # Verify Bearer prefix handling
    parsed_bearer = livekit_svc.verify_webhook(raw_body, f"Bearer {auth_token}")
    assert parsed_bearer["event"] == "participant_joined"


@pytest.mark.unit
def test_verify_webhook_mismatch_raises_error(livekit_svc: LiveKitService) -> None:
    raw_body = b'{"event":"tampered"}'
    fake_sha = "invalid_sha256_hash_value"
    auth_token = jwt.encode(
        {"sha256": fake_sha},
        livekit_svc.api_secret,
        algorithm="HS256",
    )

    with pytest.raises(ValueError, match="sha256 mismatch"):
        livekit_svc.verify_webhook(raw_body, auth_token)


@pytest.mark.unit
def test_verify_webhook_missing_header_raises_error(livekit_svc: LiveKitService) -> None:
    raw_body = b'{"event":"test"}'
    with pytest.raises(ValueError, match="Missing LiveKit webhook Authorization header"):
        livekit_svc.verify_webhook(raw_body, "")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_list_participants_default(livekit_svc: LiveKitService) -> None:
    participants = await livekit_svc.list_participants("room_empty_test")
    assert isinstance(participants, list)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_webhook_event_participant_lifecycle(
    livekit_svc: LiveKitService,
) -> None:
    # 1. participant_joined
    joined_event = {
        "event": "participant_joined",
        "room": {"name": "room_11111111-1111-1111-1111-111111111111"},
        "participant": {"identity": "part_alex_01"},
    }
    res_joined = await livekit_svc.dispatch_webhook_event(joined_event)
    assert res_joined["action"] == "participant_joined_recorded"
    assert res_joined["participant_identity"] == "part_alex_01"

    # 2. participant_left
    left_event = {
        "event": "participant_left",
        "room": {"name": "room_11111111-1111-1111-1111-111111111111"},
        "participant": {"identity": "part_alex_01"},
    }
    res_left = await livekit_svc.dispatch_webhook_event(left_event)
    assert res_left["action"] == "participant_left_recorded"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_webhook_event_track_lifecycle(
    livekit_svc: LiveKitService,
) -> None:
    # 1. track_published
    pub_event = {
        "event": "track_published",
        "room": {"name": "room_11111111-1111-1111-1111-111111111111"},
        "participant": {"identity": "part_alex_01"},
        "track": {"sid": "TR_12345", "type": "AUDIO"},
    }
    res_pub = await livekit_svc.dispatch_webhook_event(pub_event)
    assert res_pub["action"] == "track_published_registered"
    assert res_pub["track_type"] == "AUDIO"
    assert res_pub["track_sid"] == "TR_12345"

    # 2. track_unpublished
    unpub_event = {
        "event": "track_unpublished",
        "room": {"name": "room_11111111-1111-1111-1111-111111111111"},
        "participant": {"identity": "part_alex_01"},
        "track": {"sid": "TR_12345"},
    }
    res_unpub = await livekit_svc.dispatch_webhook_event(unpub_event)
    assert res_unpub["action"] == "track_unpublished_registered"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dispatch_webhook_event_room_lifecycle(
    livekit_svc: LiveKitService,
) -> None:
    # 1. room_started
    start_event = {
        "event": "room_started",
        "room": {"name": "room_11111111-1111-1111-1111-111111111111"},
    }
    res_start = await livekit_svc.dispatch_webhook_event(start_event)
    assert res_start["action"] == "room_started_synchronized"

    # 2. room_finished
    finish_event = {
        "event": "room_finished",
        "room": {"name": "room_11111111-1111-1111-1111-111111111111"},
    }
    res_finish = await livekit_svc.dispatch_webhook_event(finish_event)
    assert res_finish["action"] == "room_finished_synchronized"
