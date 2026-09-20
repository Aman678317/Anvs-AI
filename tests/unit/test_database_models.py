"""Unit tests for SQLAlchemy 2.0 Database Models."""

import uuid
from datetime import UTC, datetime

import pytest

from packages.database.models import (
    Meeting,
    Organization,
    Participant,
    TranscriptEmbedding,
    TranscriptSegment,
    User,
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
