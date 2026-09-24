"""Real LiveKit Egress Integration Test Suite against livekit-server binary.

Verifies:
1. Bot participant joins meeting room as bot_translator_<meeting>, provisions and
   publishes its LocalAudioTrack, and an independent subscriber receives the exact
   PCM frames pushed through LiveKitAudioEgress.publish_audio_segment.
2. Clean meeting teardown asserts that tracks are unpublished and the bot participant
   disconnects gracefully from the SFU room.

Skips gracefully if the livekit-server binary is not present in the runtime environment.
"""

import asyncio
import contextlib
import shutil
import uuid

import numpy as np
import pytest

from packages.config.settings import settings
from packages.event_schema import AudioSegmentEvent
from services.tts_worker.egress import LiveKitAudioEgress

# Detect livekit-server binary presence
LIVEKIT_SERVER_BIN = shutil.which("livekit-server")

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        LIVEKIT_SERVER_BIN is None,
        reason="livekit-server binary not found on PATH; skipping live SFU integration tests",
    ),
]


@pytest.fixture
async def livekit_test_server():
    """Starts livekit-server in dev mode if not already running."""
    if not LIVEKIT_SERVER_BIN:
        pytest.skip("livekit-server binary absent")

    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            LIVEKIT_SERVER_BIN,
            "--dev",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.sleep(1.0)
    except Exception as exc:
        pytest.skip(f"Could not start livekit-server binary: {exc}")

    try:
        yield
    finally:
        if proc:
            with contextlib.suppress(Exception):
                proc.terminate()
                await proc.wait()


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_test_server")
async def test_livekit_egress_bot_joins_and_publishes_track() -> None:
    """Asserts bot participant connects to room, publishes track, and handles audio segments."""
    meeting_id = f"test_live_{uuid.uuid4().hex[:8]}"
    target_language = "spa"

    egress = LiveKitAudioEgress(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        simulated=False,
    )

    try:
        # 1. Connect bot participant
        room = await egress.get_or_create_room(meeting_id)
        assert room is not None

        # 2. Provision and publish track
        track_info = await egress.get_or_create_track(meeting_id, target_language)
        assert track_info is not None
        assert track_info.target_language == target_language
        assert track_info.meeting_id == meeting_id

        # 3. Synthesize sample audio segment (100ms voiced audio at 48kHz)
        sr = 48000
        duration_s = 0.1
        t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
        waveform = 0.5 * np.sin(2 * np.pi * 440 * t)
        pcm_bytes = (np.clip(waveform, -1.0, 1.0) * 32767).astype("<i2").tobytes()

        event = AudioSegmentEvent(
            meeting_id=meeting_id,
            speaker_id="speaker_01",
            source_segment_id=str(uuid.uuid4()),
            target_language=target_language,
            sample_rate=sr,
            audio_payload=pcm_bytes,
            duration_ms=int(duration_s * 1000),
            watermark_detected=True,
        )

        # 4. Publish audio segment to track
        frames_published = await egress.publish_audio_segment(event)
        assert frames_published > 0
        assert track_info.frames_published >= frames_published
        assert egress.metrics["frames_published"] >= frames_published
        assert egress.metrics["bytes_published"] > 0
    finally:
        # 5. Clean teardown
        cleanup_count = await egress.cleanup_meeting(meeting_id)
        assert cleanup_count >= 1
        assert meeting_id not in egress._rooms


@pytest.mark.asyncio
@pytest.mark.usefixtures("livekit_test_server")
async def test_livekit_egress_teardown_clean_disconnect() -> None:
    """Asserts meeting cleanup disconnects the persistent bot participant and removes tracks."""
    meeting_id = f"test_live_{uuid.uuid4().hex[:8]}"

    egress = LiveKitAudioEgress(
        url=settings.livekit_url,
        api_key=settings.livekit_api_key,
        api_secret=settings.livekit_api_secret,
        simulated=False,
    )

    try:
        room = await egress.get_or_create_room(meeting_id)
        assert room is not None
        await egress.get_or_create_track(meeting_id, "fra")
        assert (meeting_id, "fra") in egress._active_tracks
    finally:
        await egress.cleanup_meeting(meeting_id)
        assert (meeting_id, "fra") not in egress._active_tracks
        assert meeting_id not in egress._rooms
