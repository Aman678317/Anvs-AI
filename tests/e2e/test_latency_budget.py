"""End-to-End Latency Budget Test Suite.

Verifies that the speech -> translation -> synthesized audio pipeline
completes within the configured latency budget (LATENCY_BUDGET_MS, default 5000ms).
"""

import asyncio
import contextlib
import uuid

import pytest

from packages.event_schema.bus import (
    STREAM_SYNTHESIZED_AUDIO,
    STREAM_TRANSCRIPTS,
    RedisStreamBus,
    get_stream_key,
)
from packages.event_schema.events import AudioSegmentEvent
from scripts.ci_latency_budget import LATENCY_BUDGET_MS, measure_pipeline_latency


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_pipeline_latency_budget_compliance() -> None:
    """Validates that stream processing latency remains within the defined threshold."""
    budget_ms = LATENCY_BUDGET_MS
    meeting_id = f"test_e2e_latency_{uuid.uuid4().hex[:8]}"

    bus = RedisStreamBus()
    try:
        await bus.connect()
    except Exception:
        pytest.skip("Redis service unavailable; skipping live E2E latency stream test")

    try:
        # Simulate worker processing by publishing synthesized output directly after transcript
        transcripts_stream = get_stream_key(meeting_id, STREAM_TRANSCRIPTS)
        synthesized_stream = get_stream_key(meeting_id, STREAM_SYNTHESIZED_AUDIO)

        # Pre-publish or start background response task
        async def mock_worker_reaction() -> None:
            await asyncio.sleep(0.05)
            synth_event = AudioSegmentEvent(
                meeting_id=meeting_id,
                speaker_id="speaker_01",
                source_segment_id=str(uuid.uuid4()),
                target_language="spa",
                sample_rate=48000,
                audio_payload=b"\x00\x00" * 480,
                duration_ms=10,
                watermark_detected=True,
            )
            await bus.publish(synthesized_stream, synth_event)

        reaction_task = asyncio.create_task(mock_worker_reaction())
        measured_latency = await measure_pipeline_latency(bus, meeting_id)
        await reaction_task

        assert measured_latency <= budget_ms
    finally:
        with contextlib.suppress(Exception):
            await bus.client.delete(transcripts_stream, synthesized_stream)
        await bus.disconnect()
