"""Unit tests for LiveKit Audio Subscriber and Human Source Track Gate (PR-10)."""

from unittest.mock import AsyncMock

import numpy as np
import pytest

from packages.audio.framing import float32_to_pcm_s16le
from packages.audio.watermark import embed_watermark
from packages.config import settings
from packages.event_schema import RedisStreamBus
from services.audio_ingress.service import AudioIngressService
from services.audio_ingress.subscriber import LiveKitAudioSubscriber


@pytest.mark.unit
def test_human_source_gate_filtering() -> None:
    """Verifies that Human Source Gate strictly rejects bot identities and synthetic audio tracks."""
    subscriber = LiveKitAudioSubscriber()

    # 1. Bot participant identities must be rejected
    assert subscriber.is_human_source("bot_translator_en", "microphone") is False
    assert subscriber.is_human_source("bot_tts_worker", "audio_track") is False
    assert subscriber.is_human_source("bot_ingress_001", "track_1") is False

    # 2. Translated or synthetic audio tracks must be rejected regardless of participant identity
    assert subscriber.is_human_source("user_human_alice", "translated_es_001") is False
    assert subscriber.is_human_source("user_human_bob", "synthetic_audio_pcm") is False

    # 3. Legitimate human participants must be admitted
    assert subscriber.is_human_source("user_alice_123", "microphone") is True
    assert subscriber.is_human_source("guest_bob_456", "headset_audio") is True
    assert subscriber.is_human_source("usr_charlie_789", None) is True


@pytest.mark.unit
@pytest.mark.asyncio
async def test_simulated_track_pcm_admit_and_reject() -> None:
    """Verifies that handle_simulated_track_pcm enforces gating and metrics updates."""
    mock_service = AsyncMock(spec=AudioIngressService)
    subscriber = LiveKitAudioSubscriber(ingress_service=mock_service)

    dummy_pcm = b"\x00\x00" * 960  # 20ms at 48kHz

    # 1. Bot participant track -> Rejected
    admitted = await subscriber.handle_simulated_track_pcm(
        meeting_id="m_test_1",
        participant_id="bot_translator_es",
        pcm_bytes=dummy_pcm,
        track_name="translated_es",
    )
    assert admitted is False
    assert subscriber.metrics["bot_tracks_rejected"] == 1
    assert subscriber.metrics["human_tracks_admitted"] == 0
    mock_service.ingest_audio_pcm.assert_not_called()

    # 2. Human participant track -> Admitted
    admitted = await subscriber.handle_simulated_track_pcm(
        meeting_id="m_test_1",
        participant_id="user_human_alice",
        pcm_bytes=dummy_pcm,
        track_name="microphone",
    )
    assert admitted is True
    assert subscriber.metrics["human_tracks_admitted"] == 1
    assert subscriber.metrics["frames_ingested"] == 1
    assert subscriber.metrics["bytes_ingested"] == len(dummy_pcm)
    mock_service.ingest_audio_pcm.assert_awaited_once_with(
        meeting_id="m_test_1",
        participant_id="user_human_alice",
        pcm_bytes=dummy_pcm,
        spoken_language="eng",
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscriber_end_to_end_invariant_3_watermark_rejection() -> None:
    """End-to-End Invariant #3 test: 20 kHz acoustic watermark loop is rejected at 48 kHz."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    ingress_service = AudioIngressService(stream_bus=mock_bus)
    subscriber = LiveKitAudioSubscriber(ingress_service=ingress_service)

    meeting_id = "meeting_inv3_e2e"
    participant_id = "user_human_loudspeaker_echo"

    # 1 second of 48kHz audio (48,000 samples)
    t = np.linspace(0, 1.0, 48000, endpoint=False, dtype=np.float32)
    voice_audio = 0.25 * np.sin(2 * np.pi * 400 * t)

    # Embed 20 kHz ultrasonic watermark (simulating speaker playback picking up into microphone)
    watermarked_audio = embed_watermark(voice_audio, sample_rate=48000, watermark_freq=20000.0)
    watermarked_pcm = float32_to_pcm_s16le(watermarked_audio)

    # Ingest through subscriber
    admitted = await subscriber.handle_simulated_track_pcm(
        meeting_id=meeting_id,
        participant_id=participant_id,
        pcm_bytes=watermarked_pcm,
        track_name="microphone",
    )
    assert admitted is True

    # Inspect pipeline metrics: Invariant #3 verification
    pipeline = await ingress_service.get_or_create_pipeline(meeting_id, participant_id)
    assert pipeline.watermarked_frames_dropped == 50  # 48000 / 960 = 50 frames
    assert pipeline.clean_frames_passed == 0
    assert pipeline.voiced_segments_produced == 0

    # Ensure zero events published to Redis stream
    mock_bus.publish.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscriber_end_to_end_clean_speech_publish() -> None:
    """Verifies that clean human speech passes watermark inspection, resamples to 16kHz, and publishes."""
    mock_bus = AsyncMock(spec=RedisStreamBus)
    mock_bus.publish.return_value = "msg_audio_clean_1"

    ingress_service = AudioIngressService(stream_bus=mock_bus)
    subscriber = LiveKitAudioSubscriber(ingress_service=ingress_service)

    meeting_id = "meeting_clean_e2e"
    participant_id = "user_clean_speaker"

    # 500ms speech + 500ms silence at 48kHz
    t_speech = np.linspace(0, 0.5, 24000, endpoint=False, dtype=np.float32)
    speech = 0.35 * np.sin(2 * np.pi * 500 * t_speech)
    silence = np.zeros(24000, dtype=np.float32)
    full_audio = np.concatenate((speech, silence))
    clean_pcm = float32_to_pcm_s16le(full_audio)

    admitted = await subscriber.handle_simulated_track_pcm(
        meeting_id=meeting_id,
        participant_id=participant_id,
        pcm_bytes=clean_pcm,
        track_name="microphone",
        spoken_language="eng",
    )
    assert admitted is True

    pipeline = await ingress_service.get_or_create_pipeline(meeting_id, participant_id)
    assert pipeline.clean_frames_passed == 50
    assert pipeline.watermarked_frames_dropped == 0
    assert pipeline.voiced_segments_produced >= 1

    # Verify Redis publish was triggered with AudioSegmentEvent containing canonical lineage
    assert mock_bus.publish.called
    call_args = mock_bus.publish.call_args
    event = call_args.kwargs.get("event") or call_args.args[1]

    assert event.watermarked is False
    assert event.sample_rate == 16000
    assert event.target_language == "eng"
    assert event.source_segment_id.startswith(f"src_{participant_id}_")
    assert event.correlation_id.startswith(f"corr_{meeting_id}_{participant_id}_")
    assert event.hop_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscriber_unsubscribe_and_cleanup() -> None:
    """Verifies that unsubscribe_from_room tears down active pipelines and updates metrics."""
    ingress_service = AudioIngressService()
    subscriber = LiveKitAudioSubscriber(ingress_service=ingress_service, simulated=True)

    # 1. Connect to simulated room
    room = await subscriber.subscribe_to_room(
        "meeting_to_clean", token="mock_token", simulated=True
    )
    assert room is not None
    assert subscriber.get_metrics()["active_rooms"] == 1

    # 2. Ingest frames to provision a pipeline
    dummy_pcm = b"\x00\x00" * 960
    await subscriber.handle_simulated_track_pcm("meeting_to_clean", "user_1", dummy_pcm)
    assert ingress_service.get_active_pipeline_count() == 1

    # 3. Unsubscribe
    await subscriber.unsubscribe_from_room("meeting_to_clean")
    assert subscriber.get_metrics()["active_rooms"] == 0
    assert ingress_service.get_active_pipeline_count() == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_subscriber_production_connect_failure_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that in production mode, LiveKit room connection failure raises ConnectionError."""
    monkeypatch.setattr(settings, "app_env", "production")
    ingress_service = AudioIngressService()
    subscriber = LiveKitAudioSubscriber(ingress_service=ingress_service, simulated=False)

    if subscriber.is_rtc_available:
        with pytest.raises(
            ConnectionError, match="LiveKit SFU room subscription failed in production"
        ):
            await subscriber.subscribe_to_room("prod_meeting", token="invalid_mock_token")
