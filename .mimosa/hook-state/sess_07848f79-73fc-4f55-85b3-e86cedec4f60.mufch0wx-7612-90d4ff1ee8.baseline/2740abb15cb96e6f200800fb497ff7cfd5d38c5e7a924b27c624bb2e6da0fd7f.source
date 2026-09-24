"""Contract tests for STT worker schemas and downstream subscriber compatibility."""

import base64
from unittest.mock import AsyncMock

import numpy as np
import pytest
from pydantic import ValidationError

from packages.audio.framing import float32_to_pcm_s16le
from packages.contracts import WSServerCaptionFrame
from packages.event_schema import (
    AudioSegmentEvent,
    RedisStreamBus,
    SourceSegmentEvent,
)
from services.realtime_gateway.subscriber import source_segment_to_caption_frame
from services.stt_worker import MockSTTEngine, STTConsumer


@pytest.mark.contract
def test_source_segment_event_strict_contract() -> None:
    """Verifies that SourceSegmentEvent schema forbids extra attributes and validates bounds."""
    valid_data = {
        "event_id": "evt_contract_001",
        "timestamp_ms": 1710000000000,
        "meeting_id": "meeting_contract_001",
        "tenant_id": "tenant_123",
        "session_id": "session_livekit_001",
        "participant_id": "part_contract_001",
        "source_segment_id": "src_lineage_001",
        "language": "eng",
        "text": "Hello world contract verification",
        "is_final": True,
        "start_ms": 0,
        "end_ms": 1500,
        "confidence": 0.96,
        "speaker_tag": "Speaker_A",
    }

    event = SourceSegmentEvent.model_validate(valid_data)
    assert event.language == "eng"
    assert event.confidence == 0.96

    # 1. Extra attributes forbidden
    with pytest.raises(ValidationError):
        SourceSegmentEvent.model_validate({**valid_data, "unauthorized_extra_field": "illegal"})

    # 2. Confidence must be between 0.0 and 1.0
    with pytest.raises(ValidationError):
        SourceSegmentEvent.model_validate({**valid_data, "confidence": 1.5})

    # 3. Language must be 3-character ISO-639-3 code
    with pytest.raises(ValidationError):
        SourceSegmentEvent.model_validate({**valid_data, "language": "en"})


@pytest.mark.contract
def test_stt_to_gateway_caption_frame_compatibility() -> None:
    """Verifies that SourceSegmentEvent seamlessly maps to WSServerCaptionFrame."""
    event = SourceSegmentEvent(
        event_id="evt_cap_001",
        timestamp_ms=1710000000000,
        meeting_id="meeting_cap_001",
        session_id="session_001",
        participant_id="user_host_123",
        source_segment_id="src_user_host_123_500",
        language="spa",
        text="Buenas tardes a todos",
        is_final=True,
        start_ms=500,
        end_ms=2000,
        confidence=0.98,
        speaker_tag="Host",
    )

    caption_frame = source_segment_to_caption_frame(event)

    assert isinstance(caption_frame, WSServerCaptionFrame)
    assert caption_frame.source_segment_id == "src_user_host_123_500"
    assert caption_frame.speaker_id == "user_host_123"
    assert caption_frame.source_language == "spa"
    assert caption_frame.target_language == "spa"
    assert caption_frame.text == "Buenas tardes a todos"
    assert caption_frame.is_final is True
    assert caption_frame.start_ms == 500
    assert caption_frame.end_ms == 2000


@pytest.mark.contract
@pytest.mark.asyncio
async def test_audio_segment_to_stt_pipeline_contract() -> None:
    """Verifies contract pipeline from AudioSegmentEvent to SourceSegmentEvent."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg-stt-contract"
    mock_bus.ack_event.return_value = 1

    consumer = STTConsumer(stream_bus=mock_bus, engine=MockSTTEngine(simulated_ttft_ms=0))

    audio_samples = np.zeros(8000, dtype=np.float32)
    pcm_bytes = float32_to_pcm_s16le(audio_samples)
    b64_audio = base64.b64encode(pcm_bytes).decode("utf-8")

    input_audio_event = AudioSegmentEvent(
        event_id="aud_contract_01",
        timestamp_ms=1710000000000,
        meeting_id="meeting_pipeline_contract",
        tenant_id="tenant_alpha",
        source_segment_id="src_speaker_alpha_1200",
        target_language="eng",
        audio_uri=f"base64://{b64_audio}",
        duration_ms=500,
        sample_rate=16000,
        watermarked=False,
    )

    emitted = await consumer.process_message(
        stream_name="events:meeting:meeting_pipeline_contract:audio",
        message_id="200-0",
        raw_payload=input_audio_event.model_dump(),
        meeting_id="meeting_pipeline_contract",
    )

    assert len(emitted) > 0
    final_event = emitted[-1]
    assert final_event.source_segment_id == input_audio_event.source_segment_id
    assert final_event.meeting_id == input_audio_event.meeting_id
    assert final_event.tenant_id == input_audio_event.tenant_id
    assert final_event.language == "eng"
    assert final_event.is_final is True
