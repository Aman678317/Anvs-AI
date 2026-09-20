"""Unit tests for LiveKit Webhook Endpoint."""

import base64
import hashlib
import json

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from packages.config import settings
from services.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.unit
def test_webhook_valid_event_processing(client: TestClient) -> None:
    event_payload = {
        "event": "participant_joined",
        "room": {"name": "room_test_123"},
        "participant": {
            "identity": "part_elena_1",
            "name": "Elena",
        },
    }
    raw_body = json.dumps(event_payload).encode("utf-8")
    computed_sha = base64.b64encode(hashlib.sha256(raw_body).digest()).decode("utf-8")

    auth_token = jwt.encode(
        {"sha256": computed_sha},
        settings.livekit_api_secret,
        algorithm="HS256",
    )
    headers = {"Authorization": auth_token, "Content-Type": "application/json"}

    response = client.post("/api/v1/rooms/webhook", content=raw_body, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processed"
    assert data["event"] == "participant_joined"
    assert data["room"] == "room_test_123"


@pytest.mark.unit
def test_webhook_track_published_event(client: TestClient) -> None:
    event_payload = {
        "event": "track_published",
        "room": {"name": "room_test_456"},
        "participant": {"identity": "speaker_1"},
        "track": {
            "sid": "TR_audio_1",
            "type": "AUDIO",
            "source": "MICROPHONE",
        },
    }
    raw_body = json.dumps(event_payload).encode("utf-8")
    computed_sha = base64.b64encode(hashlib.sha256(raw_body).digest()).decode("utf-8")

    auth_token = jwt.encode(
        {"sha256": computed_sha},
        settings.livekit_api_secret,
        algorithm="HS256",
    )
    headers = {"Authorization": auth_token, "Content-Type": "application/json"}

    response = client.post("/api/v1/rooms/webhook", content=raw_body, headers=headers)
    assert response.status_code == 200
    assert response.json()["event"] == "track_published"


@pytest.mark.unit
def test_webhook_invalid_signature_rejected(client: TestClient) -> None:
    raw_body = b'{"event":"tampered"}'
    fake_token = "invalid.bearer.token"
    headers = {"Authorization": fake_token, "Content-Type": "application/json"}

    response = client.post("/api/v1/rooms/webhook", content=raw_body, headers=headers)
    assert response.status_code == 400
    assert "Webhook verification failed" in response.json()["detail"]
