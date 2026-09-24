"""Unit tests for SQLAlchemy 2.0 Database Models."""

import uuid
from datetime import UTC, datetime

import pytest

from packages.database.models import (
    IdempotencyKey,
    Meeting,
    MeetingChatMessage,
    MeetingSetting,
    Organization,
    OrganizationMember,
    OutboxEvent,
    Participant,
    SourceSegment,
    TranscriptEmbedding,
    TranscriptSegment,
    User,
    UserSession,
    VoiceProfile,
)


@pytest.mark.unit
def test_organization_model_instantiation() -> None:
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name="Acme Corporation",
        slug="acme-corp",
    )
    assert org.id == org_id
    assert org.name == "Acme Corporation"
    assert org.slug == "acme-corp"
    assert Organization.__tablename__ == "organizations"


@pytest.mark.unit
def test_user_model_instantiation() -> None:
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="alex.chen@acme.com",
        full_name="Alex Chen",
        role="HOST",
        default_spoken_language="eng",
        default_listening_language="fra",
        is_active=True,
    )
    assert user.id == user_id
    assert user.tenant_id == tenant_id
    assert user.email == "alex.chen@acme.com"
    assert user.role == "HOST"
    assert user.default_spoken_language == "eng"
    assert user.default_listening_language == "fra"
    assert user.is_active is True
    assert User.__tablename__ == "users"


@pytest.mark.unit
def test_meeting_model_lifecycle_defaults() -> None:
    meeting_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    creator_id = uuid.uuid4()
    now = datetime.now(UTC)

    meeting = Meeting(
        id=meeting_id,
        tenant_id=tenant_id,
        created_by=creator_id,
        title="Q3 Global Product Review",
        status="SCHEDULED",
        state_version=1,
        host_spoken_language="eng",
        host_listening_language="deu",
        scheduled_start=now,
    )
    assert meeting.id == meeting_id
    assert meeting.tenant_id == tenant_id
    assert meeting.status == "SCHEDULED"
    assert meeting.state_version == 1
    assert meeting.host_spoken_language == "eng"
    assert meeting.host_listening_language == "deu"
    assert Meeting.__tablename__ == "meetings"


@pytest.mark.unit
def test_participant_model_instantiation() -> None:
    part_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()

    participant = Participant(
        id=part_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        display_name="Dr. Hans Richter",
        role="PARTICIPANT",
        spoken_language="deu",
        listening_language="eng",
        is_muted=True,
        is_video_enabled=False,
    )
    assert participant.id == part_id
    assert participant.display_name == "Dr. Hans Richter"
    assert participant.role == "PARTICIPANT"
    assert participant.spoken_language == "deu"
    assert participant.listening_language == "eng"
    assert participant.is_muted is True
    assert participant.is_video_enabled is False
    assert Participant.__tablename__ == "participants"


@pytest.mark.unit
def test_transcript_segment_lineage_preservation() -> None:
    seg_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()

    segment = TranscriptSegment(
        id=seg_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        source_segment_id="src-lineage-777",
        speaker_id="spk-1",
        speaker_name="Alex Chen",
        source_language="eng",
        target_language="deu",
        original_text="We must finalize our deployment plan.",
        translated_text="Wir müssen unseren Einsatzplan fertigstellen.",
        start_ms=0,
        end_ms=2800,
        confidence=0.98,
        is_final=True,
    )
    assert segment.id == seg_id
    assert segment.source_segment_id == "src-lineage-777"
    assert segment.confidence == 0.98
    assert segment.is_final is True
    assert TranscriptSegment.__tablename__ == "transcript_segments"


@pytest.mark.unit
def test_transcript_embedding_model() -> None:
    emb_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()
    segment_id = uuid.uuid4()

    dummy_vector = [0.0] * 1536
    embedding = TranscriptEmbedding(
        id=emb_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        segment_id=segment_id,
        content="We must finalize our deployment plan.",
        embedding=dummy_vector,
    )
    assert embedding.id == emb_id
    assert embedding.segment_id == segment_id
    assert len(embedding.embedding) == 1536
    assert TranscriptEmbedding.__tablename__ == "transcript_embeddings"


@pytest.mark.unit
def test_user_session_model() -> None:
    session_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    expires = datetime.now(UTC)

    session = UserSession(
        id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        refresh_token_hash="hash-abc-123",
        user_agent="Mozilla/5.0 Chrome/120.0",
        ip_address="192.168.1.100",
        is_revoked=False,
        expires_at=expires,
    )
    assert session.id == session_id
    assert session.tenant_id == tenant_id
    assert session.user_id == user_id
    assert session.refresh_token_hash == "hash-abc-123"
    assert session.is_revoked is False
    assert UserSession.__tablename__ == "user_sessions"


@pytest.mark.unit
def test_organization_member_model() -> None:
    member_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    member = OrganizationMember(
        id=member_id,
        tenant_id=tenant_id,
        user_id=user_id,
        role="ADMIN",
        is_active=True,
    )
    assert member.id == member_id
    assert member.tenant_id == tenant_id
    assert member.user_id == user_id
    assert member.role == "ADMIN"
    assert member.is_active is True
    assert OrganizationMember.__tablename__ == "organization_members"


@pytest.mark.unit
def test_meeting_setting_model() -> None:
    setting_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()

    setting = MeetingSetting(
        id=setting_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        enable_recording=True,
        enable_transcription=True,
        enable_translation=True,
        enable_voice_cloning=True,
        retention_days=60,
        allowed_languages=["eng", "spa", "fra"],
        extra_features={"ai_assistant": True},
    )
    assert setting.id == setting_id
    assert setting.meeting_id == meeting_id
    assert setting.enable_recording is True
    assert setting.retention_days == 60
    assert "eng" in setting.allowed_languages
    assert MeetingSetting.__tablename__ == "meeting_settings"


@pytest.mark.unit
def test_source_segment_model() -> None:
    segment_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()

    segment = SourceSegment(
        id=segment_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        source_segment_id="src-lineage-001",
        speaker_id="spk-1",
        speaker_name="Sarah Connor",
        language="eng",
        text="Starting the technical briefing.",
        start_ms=0,
        end_ms=2500,
        confidence=0.99,
        is_final=True,
    )
    assert segment.id == segment_id
    assert segment.source_segment_id == "src-lineage-001"
    assert segment.language == "eng"
    assert segment.confidence == 0.99
    assert SourceSegment.__tablename__ == "source_segments"


@pytest.mark.unit
def test_voice_profile_model() -> None:
    profile_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    dummy_vec = [0.1] * 256

    profile = VoiceProfile(
        id=profile_id,
        tenant_id=tenant_id,
        user_id=user_id,
        speaker_name="Sarah Connor",
        embedding=dummy_vec,
        sample_rate=16000,
        duration_sec=15.5,
        is_verified=True,
    )
    assert profile.id == profile_id
    assert profile.speaker_name == "Sarah Connor"
    assert len(profile.embedding) == 256
    assert profile.is_verified is True
    assert VoiceProfile.__tablename__ == "voice_profiles"


@pytest.mark.unit
def test_meeting_chat_model() -> None:
    chat_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    meeting_id = uuid.uuid4()
    sender_id = uuid.uuid4()

    msg = MeetingChatMessage(
        id=chat_id,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
        sender_id=sender_id,
        sender_name="Sarah Connor",
        content="Welcome team!",
        language="eng",
        translated_content={"spa": "¡Bienvenidos equipo!"},
    )
    assert msg.id == chat_id
    assert msg.content == "Welcome team!"
    assert msg.translated_content["spa"] == "¡Bienvenidos equipo!"
    assert MeetingChatMessage.__tablename__ == "meeting_chat"


@pytest.mark.unit
def test_outbox_event_model() -> None:
    outbox_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    event = OutboxEvent(
        id=outbox_id,
        tenant_id=tenant_id,
        aggregate_type="meeting",
        aggregate_id="mtg-123",
        event_type="meeting.started",
        payload={"meeting_id": "mtg-123"},
        is_published=False,
        retry_count=0,
    )
    assert event.id == outbox_id
    assert event.aggregate_type == "meeting"
    assert event.event_type == "meeting.started"
    assert event.is_published is False
    assert OutboxEvent.__tablename__ == "outbox_events"


@pytest.mark.unit
def test_idempotency_key_model() -> None:
    key_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    expires = datetime.now(UTC)

    key = IdempotencyKey(
        id=key_id,
        tenant_id=tenant_id,
        key="idemp-key-xyz-789",
        target_endpoint="/api/v1/rooms",
        response_code=201,
        response_body='{"status":"created"}',
        expires_at=expires,
    )
    assert key.id == key_id
    assert key.key == "idemp-key-xyz-789"
    assert key.response_code == 201
    assert IdempotencyKey.__tablename__ == "idempotency_keys"
