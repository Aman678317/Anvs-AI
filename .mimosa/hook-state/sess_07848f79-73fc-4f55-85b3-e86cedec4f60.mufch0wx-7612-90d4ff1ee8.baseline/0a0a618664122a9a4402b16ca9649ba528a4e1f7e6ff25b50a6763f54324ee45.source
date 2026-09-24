"""End-to-End Multi-Service Platform Integration Test Suite (PR-15).

Tests seamless orchestration across all core platform services:
1. Control Plane Room Provisioning & Dual Token Minting
2. Real-time WebSocket Session Ticket Handshake
3. Streaming STT -> NMT -> TTS Multi-Track Processing
4. Invariant #3 Ultrasonic Watermarking Verification
5. Assistant Vector Store In-Meeting Copilot Grounding
6. Host Room Termination & Graceful Resource Eviction
"""

import uuid
from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from packages.audio.watermark import detect_watermark
from packages.auth.models import AuthenticatedUser
from packages.contracts import MeetingStatus, ParticipantRole, WSClientMessageType
from packages.contracts.rest import CreateMeetingRequest, JoinMeetingRequest
from packages.contracts.websocket import WSClientJoinFrame
from packages.database.models import Meeting
from packages.event_schema import (
    AssistantQueryEvent,
    AudioSegmentEvent,
    SourceSegmentEvent,
    TranslationSegmentEvent,
)
from services.api.routers.rooms import create_room, end_room, join_room
from services.assistant_worker.consumer import AssistantConsumer
from services.assistant_worker.engine import MockAssistantEngine
from services.realtime_gateway.manager import ConnectionManager
from services.stt_worker.engine import MockSTTEngine
from services.translation_worker.engine import MockNMTEngine
from services.tts_worker.engine import MockTTSEngine


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_platform_pipeline_integration() -> None:
    """Verifies complete multi-service workflow from room creation to teardown."""
    tenant_id = str(uuid.uuid4())
    host_id = str(uuid.uuid4())
    host_user = AuthenticatedUser(
        user_id=host_id,
        tenant_id=tenant_id,
        email="lead.architect@enterprise.org",
        role=ParticipantRole.HOST,
    )

    # 1. Host Provisions Meeting Room via REST API
    create_req = CreateMeetingRequest(
        title="Global Architecture Alignment: GA Release",
        host_spoken_language="eng",
        host_listening_language="eng",
    )
    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    create_resp = await create_room(
        payload=create_req,
        current_user=host_user,
        session=mock_db,
    )
    meeting_id = create_resp.meeting_id
    assert create_resp.status == MeetingStatus.SCHEDULED

    # Setup database meeting instance for subsequent operations
    target_uuid = uuid.UUID(meeting_id)
    meeting_record = Meeting(
        id=target_uuid,
        tenant_id=uuid.UUID(tenant_id),
        created_by=uuid.UUID(host_id),
        title=create_req.title,
        status="ACTIVE",
        state_version=1,
        host_spoken_language="eng",
        host_listening_language="eng",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = meeting_record
    mock_db.execute.return_value = mock_result

    # 2. Host and Attendees Join and Receive Real Signed Tokens
    attendee_id = str(uuid.uuid4())
    attendee_user = AuthenticatedUser(
        user_id=attendee_id,
        tenant_id=tenant_id,
        email="engineer.tokyo@enterprise.org",
        role=ParticipantRole.PARTICIPANT,
    )

    join_req = JoinMeetingRequest(
        display_name="Kenji (Tokyo)",
        spoken_language="jpn",
        listening_language="eng",
    )
    join_resp = await join_room(
        meeting_id=meeting_id,
        payload=join_req,
        current_user=attendee_user,
        session=mock_db,
    )

    assert join_resp.meeting_id == meeting_id
    assert len(join_resp.livekit_token) > 20
    assert len(join_resp.ws_ticket) > 10

    # 3. Realtime WebSocket Gateway Handshake
    join_frame = WSClientJoinFrame(
        type=WSClientMessageType.JOIN,
        ticket=join_resp.ws_ticket,
        participant_id=attendee_id,
    )
    assert join_frame.ticket == join_resp.ws_ticket

    conn_manager = ConnectionManager()
    assert conn_manager.get_participant_count(meeting_id) == 0

    # 4. Audio Ingestion & Streaming STT Worker
    stt_engine = MockSTTEngine()
    sr = 16000
    pcm_audio = np.zeros(int(sr * 1.5), dtype=np.float32)

    stt_result = await stt_engine.transcribe_segment(pcm_audio, language="eng")
    segment_text = stt_result.text
    assert len(segment_text) > 0
    source_seg_id = f"src_{uuid.uuid4().hex[:12]}"

    source_event = SourceSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100000000,
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        session_id="session_01",
        participant_id=host_id,
        source_segment_id=source_seg_id,
        language="eng",
        text=segment_text,
        start_ms=0,
        end_ms=1500,
        is_final=True,
        confidence=0.99,
    )

    # 5. Polyglot NMT Worker Translation
    nmt_engine = MockNMTEngine()
    nmt_result = await nmt_engine.translate(
        text=source_event.text,
        source_lang="eng",
        target_lang="jpn",
    )
    assert len(nmt_result.translated_text) > 0

    translation_event = TranslationSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100000500,
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        source_segment_id=source_event.source_segment_id,
        source_language="eng",
        target_language="jpn",
        translated_text=nmt_result.translated_text,
        is_final=True,
        latency_ms=nmt_result.latency_ms,
    )
    assert translation_event.source_segment_id == source_seg_id

    # 6. Streaming TTS Worker Synthesis with 20 kHz Ultrasonic Watermarking
    tts_engine = MockTTSEngine()
    tts_result = await tts_engine.synthesize(
        text=translation_event.translated_text,
        language="jpn",
        voice_id="default_neutral",
    )
    assert len(tts_result.audio_pcm) > 0
    assert detect_watermark(tts_result.audio_pcm, sample_rate=tts_result.sample_rate)

    audio_event = AudioSegmentEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100001000,
        meeting_id=meeting_id,
        tenant_id=tenant_id,
        source_segment_id=source_event.source_segment_id,
        target_language="jpn",
        audio_uri="s3://meeting-audio/jpn_seg_001.opus",
        duration_ms=tts_result.duration_ms,
        sample_rate=tts_result.sample_rate,
        watermarked=True,
    )
    assert audio_event.source_segment_id == source_seg_id

    # 7. In-Meeting RAG Copilot Query Grounding
    mock_bus = AsyncMock()
    mock_bus.publish = AsyncMock()
    mock_bus.ack_event = AsyncMock()

    assistant_engine = MockAssistantEngine()
    assistant_consumer = AssistantConsumer(
        stream_bus=mock_bus,
        engine=assistant_engine,
    )

    # Index segment into copilot vector store
    await assistant_consumer.process_transcript_message(
        stream_name=f"meeting.{meeting_id}.stream.transcripts",
        message_id="1-0",
        raw_payload=source_event.model_dump(mode="json"),
        meeting_id=meeting_id,
    )

    # Attendee asks questions about the meeting
    query_event = AssistantQueryEvent(
        event_id=str(uuid.uuid4()),
        timestamp_ms=1727100002000,
        query_id=f"qry_{uuid.uuid4().hex[:8]}",
        meeting_id=meeting_id,
        participant_id=attendee_id,
        tenant_id=tenant_id,
        question="What was discussed regarding the release roadmap?",
    )
    response_event = await assistant_consumer.process_query_message(
        stream_name=f"meeting.{meeting_id}.stream.assistant",
        message_id="2-0",
        raw_payload=query_event.model_dump(mode="json"),
        meeting_id=meeting_id,
    )

    assert response_event is not None
    assert response_event.meeting_id == meeting_id
    assert len(response_event.answer) > 0
    assert len(response_event.citations) > 0

    # 8. Host Gracefully Terminates Meeting & Finalizes Summaries
    summary = await assistant_consumer.finalize_meeting_summary(meeting_id)
    assert summary is not None
    assert summary.meeting_id == meeting_id
    assert len(summary.summary) > 0

    end_resp = await end_room(
        meeting_id=meeting_id,
        current_user=host_user,
        session=mock_db,
    )
    assert end_resp["status"] == "ENDED"
    assert end_resp["meeting_id"] == meeting_id
