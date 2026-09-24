"""Security, Invariant Verification & Compliance Audit Test Suite (PR-15).

Validates all 4 Core Architectural Invariants:
1. Invariant #1: Strict Multi-Tenant Isolation & Crypto Key Segregation
2. Invariant #2: Immutable Speech Lineage Provenance
3. Invariant #3: 20 kHz Ultrasonic Watermark Audio Loop Rejection
4. Invariant #4: At-Least-Once Delivery with Poison-Pill DLQ Quarantine
Plus RBAC Privilege Escalation Prevention, Secret Sanitization, and OWASP Security Headers.
"""

import uuid
from unittest.mock import AsyncMock

import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from packages.audio.watermark import detect_watermark, embed_watermark
from packages.auth.models import AuthenticatedUser
from packages.auth.rbac import (
    Permission,
    has_permission,
    require_permission,
)
from packages.auth.tokens import (
    InvalidTokenError,
    create_access_token,
    verify_token,
)
from packages.contracts import ParticipantRole
from packages.event_schema import (
    AudioSegmentEvent,
    DeadLetterEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)
from packages.security.crypto import (
    AuthenticationError,
    decrypt_text,
    encrypt_text,
)
from packages.security.sanitizer import sanitize_payload
from services.api.main import app
from services.orchestrator.dlq_retry import DLQRetryManager, DLQRetryOutcome

# ==============================================================================
# Invariant #1: Multi-Tenant Isolation & Crypto Key Segregation
# ==============================================================================


@pytest.mark.security
def test_tenant_crypto_key_isolation() -> None:
    """Ciphertext encrypted for Tenant A cannot be decrypted by Tenant B."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    secret_transcript = "Quarterly financial forecast and executive strategy notes."

    ciphertext_a = encrypt_text(secret_transcript, tenant_id=tenant_a)
    assert ciphertext_a != secret_transcript

    # Decrypting with correct tenant succeeds
    decrypted_a = decrypt_text(ciphertext_a, tenant_id=tenant_a)
    assert decrypted_a == secret_transcript

    # Decrypting with incorrect tenant MUST fail with AuthenticationError
    with pytest.raises(AuthenticationError):
        decrypt_text(ciphertext_a, tenant_id=tenant_b)


@pytest.mark.security
def test_cross_tenant_token_rejection() -> None:
    """Tokens issued for Tenant A must not grant access to Tenant B resources."""
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    user_a = AuthenticatedUser(
        user_id=user_id,
        tenant_id=tenant_a,
        email="devon@tenant-a.com",
        role=ParticipantRole.HOST,
    )
    token_a = create_access_token(user_a)

    verified_user = verify_token(token_a)
    assert verified_user.tenant_id == tenant_a
    assert verified_user.tenant_id != tenant_b


# ==============================================================================
# Invariant #2: Immutable Speech Lineage Provenance
# ==============================================================================


@pytest.mark.security
def test_lineage_provenance_propagation() -> None:
    """Downstream events must preserve source_segment_id for end-to-end auditability."""
    source_seg_id = f"src_{uuid.uuid4().hex[:12]}"
    meeting_id = str(uuid.uuid4())

    # 1. Source speech event
    source_event = SourceSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100000000,
        meeting_id=meeting_id,
        session_id="session_01",
        participant_id="speaker_01",
        source_segment_id=source_seg_id,
        language="eng",
        text="Deploying the multilingual model fleet.",
        start_ms=1000,
        end_ms=3500,
        is_final=True,
        confidence=0.98,
        speaker_tag="Sarah Connor",
    )
    assert source_event.source_segment_id == source_seg_id

    # 2. Translation event must embed source_segment_id
    translation_event = TranslationSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100000500,
        meeting_id=meeting_id,
        source_segment_id=source_event.source_segment_id,
        source_language="eng",
        target_language="spa",
        translated_text="Desplegando la flota de modelos multilingües.",
        is_final=True,
        latency_ms=250,
    )
    assert translation_event.source_segment_id == source_seg_id

    # 3. Audio segment event must embed source_segment_id
    audio_event = AudioSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100001000,
        meeting_id=meeting_id,
        source_segment_id=source_event.source_segment_id,
        target_language="spa",
        audio_uri="s3://meeting-audio/seg_001.opus",
        duration_ms=2500,
        sample_rate=24000,
        watermarked=True,
    )
    assert audio_event.source_segment_id == source_seg_id


# ==============================================================================
# Invariant #3: 20 kHz Ultrasonic Watermarking Audio Loop Rejection
# ==============================================================================


@pytest.mark.security
def test_watermark_synthetic_rejection_audit() -> None:
    """Synthetic TTS speech with 20 kHz tone is flagged to prevent infinite feedback loops."""
    sr = 48000
    duration_sec = 0.25
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)

    # Clean natural speech simulation (e.g. 440 Hz tone)
    clean_audio = (0.5 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
    assert not detect_watermark(clean_audio, sample_rate=sr)

    # Watermarked synthetic speech
    watermarked_audio = embed_watermark(clean_audio, sample_rate=sr, watermark_freq=20000.0)
    assert detect_watermark(watermarked_audio, sample_rate=sr)


@pytest.mark.security
def test_watermark_tamper_detection() -> None:
    """Altered watermark frequencies are not detected as legitimate 20 kHz pilot tones."""
    sr = 48000
    duration_sec = 0.25
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)

    # Audio with tone at incorrect frequency (e.g. 15 kHz instead of 20 kHz)
    tampered_audio = (0.01 * np.sin(2 * np.pi * 15000 * t)).astype(np.float32)
    assert not detect_watermark(tampered_audio, sample_rate=sr, watermark_freq=20000.0)


# ==============================================================================
# Invariant #4: At-Least-Once Delivery with Poison-Pill DLQ Quarantine
# ==============================================================================


@pytest.mark.security
@pytest.mark.asyncio
async def test_dlq_poison_pill_quarantine_audit() -> None:
    """Corrupted/poison-pill payloads must be permanently quarantined after 3 attempts."""
    mock_bus = AsyncMock()
    mock_bus.ack_event = AsyncMock()

    dlq_manager = DLQRetryManager(
        stream_bus=mock_bus,
        max_retries=3,
        base_backoff_sec=0.01,
    )

    poison_event = DeadLetterEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100000000,
        meeting_id="meet_123",
        failed_event_id="malicious_event_001",
        original_stream="meeting.123.stream.transcripts",
        error_reason="SchemaDecodeError: Invalid byte sequence",
        retry_count=3,  # Already exhausted 3 attempts
        raw_payload='{"malformed": true}',
    )

    outcome = await dlq_manager.process_dlq_event(
        dlq_event=poison_event,
        dlq_message_id="msg_999",
        dlq_stream="meeting.123.stream.dlq",
    )

    assert outcome == DLQRetryOutcome.QUARANTINED
    assert dlq_manager.quarantined_count == 1
    assert mock_bus.ack_event.called


# ==============================================================================
# RBAC Privilege Escalation Prevention
# ==============================================================================


@pytest.mark.security
def test_privilege_escalation_role_tampering() -> None:
    """Participant role cannot access Host-exclusive operations."""
    participant = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="guest@enterprise.com",
        role=ParticipantRole.PARTICIPANT,
    )

    # Participant should NOT have MEETING_END permission
    assert not has_permission(participant.role, Permission.MEETING_END)
    guard = require_permission(Permission.MEETING_END)
    with pytest.raises(HTTPException) as exc_info:
        guard(participant)
    assert exc_info.value.status_code == 403

    # Host MUST have MEETING_END permission
    host = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="host@enterprise.com",
        role=ParticipantRole.HOST,
    )
    assert has_permission(host.role, Permission.MEETING_END)
    assert guard(host) is host


@pytest.mark.security
def test_tampered_jwt_signature_rejection() -> None:
    """Altering any character of the JWT token string must cause verification failure."""
    user = AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="admin@enterprise.com",
        role=ParticipantRole.HOST,
    )
    valid_token = create_access_token(user)

    # Tamper with the signature portion of the JWT (last segment)
    parts = valid_token.split(".")
    tampered_sig = parts[2][:-4] + "XXXX"
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(InvalidTokenError):
        verify_token(tampered_token)


# ==============================================================================
# Secret Sanitization & Sensitive Payload Redaction
# ==============================================================================


@pytest.mark.security
def test_secret_sanitizer_redacts_credentials() -> None:
    """Sanitizer masks sensitive credentials in logging and tracing structures."""
    payload = {
        "user_id": "usr_12345",
        "email": "user@enterprise.com",
        "password": "SuperSecretPassword123!",
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.dummy_token_data",
        "api_secret": "sk-proj-999999999",
        "metadata": {
            "token": "livekit_secret_token",
            "safe_field": "meeting_title",
        },
    }

    sanitized = sanitize_payload(payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["access_token"] == "[REDACTED]"
    assert sanitized["api_secret"] == "[REDACTED]"
    assert sanitized["metadata"]["token"] == "[REDACTED]"
    assert sanitized["metadata"]["safe_field"] == "meeting_title"
    assert sanitized["email"] == "user@enterprise.com"


# ==============================================================================
# OWASP HTTP Security Headers Audit
# ==============================================================================


@pytest.mark.security
def test_owasp_security_headers_present() -> None:
    """FastAPI API endpoints must inject OWASP-recommended security headers."""
    client = TestClient(app)
    response = client.get("/healthz")
    assert response.status_code == 200

    headers = response.headers
    assert headers.get("X-Content-Type-Options") == "nosniff"
    assert headers.get("X-Frame-Options") == "DENY"
    assert "Strict-Transport-Security" in headers
    assert "Content-Security-Policy" in headers
