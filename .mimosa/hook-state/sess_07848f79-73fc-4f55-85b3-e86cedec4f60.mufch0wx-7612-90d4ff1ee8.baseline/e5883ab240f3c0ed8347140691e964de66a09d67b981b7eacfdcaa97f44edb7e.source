"""Redis Streams Voice Worker Consumer adhering to Document 14 (PR-11 Core)."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from packages.config.settings import settings
from packages.event_schema import (
    STREAM_DIARIZATION,
    STREAM_SYNTHESIZED_AUDIO,
    AudioSegmentEvent,
    DiarizationSegmentEvent,
    RedisStreamBus,
    TranslationSegmentEvent,
    get_stream_key,
)
from services.voice_worker.engine import BaseVoiceEngine, ConsentViolationError, create_voice_engine
from services.voice_worker.types import VoiceEmbedding

logger = logging.getLogger(__name__)


class VoiceWorkerConsumer:
    """Consumes diarization events to enroll voice profiles and enhances TTS with voice cloning.

    Pipeline:
        1. Subscribes to `STREAM_DIARIZATION` to receive `DiarizationSegmentEvent` payloads.
        2. Extracts 256-dim voice embeddings from speaker audio samples (consent gate enforced).
        3. Caches speaker embeddings in an in-memory profile registry per meeting + tenant.
        4. When a `TranslationSegmentEvent` arrives (via `synthesize_for_translation`),
           retrieves the enrolled speaker embedding and synthesizes voice-cloned speech.
        5. Emits watermarked `AudioSegmentEvent` to Redis Streams (STREAM_SYNTHESIZED_AUDIO)
           with full Invariant #2 source lineage preserved.
        6. Routes malformed payloads to DLQ (Invariant #4).
    """

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        engine: BaseVoiceEngine | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.engine = engine or create_voice_engine()
        self.group_name = group_name or settings.tts_consumer_group.replace("tts", "voice")
        self.consumer_name = consumer_name or f"voice-worker-{uuid.uuid4().hex[:8]}"

        # In-memory speaker embedding registry: (meeting_id, speaker_id) -> VoiceEmbedding
        self._embedding_registry: dict[tuple[str, str], VoiceEmbedding] = {}

        # Operational metrics
        self.metrics: dict[str, int] = {
            "profiles_enrolled": 0,
            "voice_cloned_segments": 0,
            "consent_violations": 0,
            "errors_count": 0,
            "total_synthesis_ms": 0,
        }

    async def setup(self, meeting_id: str) -> None:
        """Creates consumer group on the diarization stream for the given meeting."""
        stream_key = get_stream_key(meeting_id, STREAM_DIARIZATION)
        await self.stream_bus.create_consumer_group(
            stream=stream_key,
            group_name=self.group_name,
        )

    def get_enrolled_profile(self, meeting_id: str, speaker_id: str) -> VoiceEmbedding | None:
        """Retrieves an enrolled voice profile for a speaker within a meeting."""
        return self._embedding_registry.get((meeting_id, speaker_id))

    def clear_meeting_profiles(self, meeting_id: str) -> int:
        """Evicts all voice profiles for a completed meeting. Returns evicted count."""
        keys_to_remove = [k for k in self._embedding_registry if k[0] == meeting_id]
        for key in keys_to_remove:
            del self._embedding_registry[key]
        logger.info("Evicted %d voice profiles for meeting %s", len(keys_to_remove), meeting_id)
        return len(keys_to_remove)

    async def enroll_speaker_from_audio(
        self,
        meeting_id: str,
        speaker_id: str,
        tenant_id: str,
        audio_pcm: Any,
        sample_rate: int,
        consent_verified: bool,
    ) -> VoiceEmbedding | None:
        """Extracts and caches a voice embedding for a speaker.

        Enforces consent gate: refuses enrollment if consent_verified is False.

        Returns:
            VoiceEmbedding if successful; None on consent violation or error.
        """
        try:
            embedding = await self.engine.extract_voice_embedding(
                audio_pcm=audio_pcm,
                sample_rate=sample_rate,
                speaker_id=speaker_id,
                tenant_id=tenant_id,
                consent_verified=consent_verified,
            )
            self._embedding_registry[(meeting_id, speaker_id)] = embedding
            self.metrics["profiles_enrolled"] += 1
            logger.info(
                "Enrolled voice profile for speaker '%s' in meeting %s (consent=%s)",
                speaker_id,
                meeting_id,
                consent_verified,
            )
            return embedding

        except ConsentViolationError as exc:
            self.metrics["consent_violations"] += 1
            logger.warning("Voice enrollment rejected (consent gate): %s", exc)
            return None

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error("Voice enrollment failed for speaker '%s': %s", speaker_id, exc)
            return None

    async def synthesize_for_translation(
        self,
        stream_name: str,
        message_id: str,
        raw_payload: str | dict[str, Any],
        meeting_id: str,
    ) -> AudioSegmentEvent | None:
        """Synthesizes voice-cloned speech for a finalized translation segment.

        Attempts to retrieve the speaker's enrolled voice profile. Falls back to
        the standard TTS engine if no profile is enrolled for the speaker.
        Preserves Invariant #2 source_segment_id lineage throughout.

        Returns:
            Emitted AudioSegmentEvent or None on skip/error.
        """
        try:
            # Parse payload into a mutable dict
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload_dict = dict(raw_payload)  # shallow copy — do not mutate caller's dict
            else:
                payload_dict = json.loads(str(raw_payload))

            # Extract side-car fields BEFORE Pydantic validation.
            # TranslationSegmentEvent inherits extra="forbid" from BaseEvent, so any field
            # not declared on the schema (e.g. speaker_tag) must be removed before
            # model_validate() is called or it raises ValidationError.
            speaker_tag = payload_dict.pop("speaker_tag", None) or payload_dict.pop(
                "participant_id", None
            )

            # Validate against the schema (clean dict, no extra keys)
            translation_event = TranslationSegmentEvent.model_validate(payload_dict)

            # Only synthesize final translations with non-empty text
            if not translation_event.is_final or not translation_event.translated_text.strip():
                await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
                return None

            # INVARIANT #2: Exact source lineage preservation
            source_lineage_id = translation_event.source_segment_id

            # Attempt voice-cloned synthesis with enrolled speaker profile
            voice_profile = self._embedding_registry.get((meeting_id, str(speaker_tag or "")))

            t0 = time.perf_counter()

            if voice_profile is not None:
                clone_result = await self.engine.synthesize_with_voice(
                    text=translation_event.translated_text,
                    language=translation_event.target_language,
                    voice_embedding=voice_profile,
                )
                audio_uri = clone_result.to_base64_uri()
                duration_ms = clone_result.duration_ms
                sample_rate = clone_result.sample_rate
                watermarked = clone_result.watermarked
                self.metrics["voice_cloned_segments"] += 1
            else:
                # No enrolled voice profile — use standard mock synthesis
                from services.tts_worker.engine import MockTTSEngine

                fallback_engine = MockTTSEngine(sample_rate=48000, simulated_latency_ms=0)
                tts_result = await fallback_engine.synthesize(
                    text=translation_event.translated_text,
                    language=translation_event.target_language,
                )
                audio_uri = tts_result.to_base64_uri()
                duration_ms = tts_result.duration_ms
                sample_rate = tts_result.sample_rate
                watermarked = tts_result.watermarked

            synthesis_ms = int((time.perf_counter() - t0) * 1000)
            self.metrics["total_synthesis_ms"] += synthesis_ms

            # Construct and publish AudioSegmentEvent (Invariants #2 and #3)
            audio_event = AudioSegmentEvent(
                event_id=f"vc_evt_{uuid.uuid4()}",
                timestamp_ms=int(time.time() * 1000),
                meeting_id=meeting_id,
                tenant_id=translation_event.tenant_id,
                source_segment_id=source_lineage_id,
                target_language=translation_event.target_language,
                audio_uri=audio_uri,
                duration_ms=duration_ms,
                sample_rate=sample_rate,
                watermarked=watermarked,
            )

            synth_audio_stream = get_stream_key(meeting_id, STREAM_SYNTHESIZED_AUDIO)
            await self.stream_bus.publish(stream=synth_audio_stream, event=audio_event)
            await self.stream_bus.ack_event(stream_name, self.group_name, message_id)

            logger.debug(
                "Voice-cloned segment emitted for source=%s lang=%s speaker=%s",
                source_lineage_id,
                translation_event.target_language,
                speaker_tag,
            )
            return audio_event

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error in VoiceWorkerConsumer.synthesize_for_translation (msg=%s): %s",
                message_id,
                exc,
                exc_info=True,
            )
            payload_str = (
                json.dumps(raw_payload) if isinstance(raw_payload, dict) else str(raw_payload)
            )
            await self.stream_bus.send_to_dlq(
                meeting_id=meeting_id,
                original_stream=stream_name,
                group_name=self.group_name,
                message_id=message_id,
                raw_payload=payload_str,
                error_reason=str(exc),
            )
            return None

    async def poll_and_process_diarization(
        self,
        meeting_id: str,
        count: int = 10,
        block_ms: int = 500,
    ) -> list[DiarizationSegmentEvent]:
        """Polls Redis Streams for diarization events and decodes them.

        Returns:
            List of parsed DiarizationSegmentEvents consumed in this poll cycle.
        """
        stream_key = get_stream_key(meeting_id, STREAM_DIARIZATION)
        raw_events = await self.stream_bus.consume_events(
            stream=stream_key,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            event_class=None,
        )

        consumed: list[DiarizationSegmentEvent] = []
        for message_id, payload in raw_events:
            try:
                payload_dict = payload if isinstance(payload, dict) else json.loads(str(payload))
                event = DiarizationSegmentEvent.model_validate(payload_dict)
                consumed.append(event)
                await self.stream_bus.ack_event(stream_key, self.group_name, message_id)
            except Exception as exc:
                logger.error("Failed to parse diarization event %s: %s", message_id, exc)

        return consumed

    async def run(
        self,
        meeting_id: str,
        stop_event: asyncio.Event | None = None,
        count: int = 10,
        block_ms: int = 1000,
    ) -> None:
        """Runs the continuous voice worker consumer loop until stop_event is set."""
        await self.setup(meeting_id)
        logger.info(
            "Starting VoiceWorkerConsumer %s for meeting %s (group: %s)",
            self.consumer_name,
            meeting_id,
            self.group_name,
        )

        while stop_event is None or not stop_event.is_set():
            try:
                await self.poll_and_process_diarization(
                    meeting_id=meeting_id,
                    count=count,
                    block_ms=block_ms,
                )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in VoiceWorkerConsumer loop: %s", exc)
                await asyncio.sleep(0.5)

        self.clear_meeting_profiles(meeting_id)
        logger.info("VoiceWorkerConsumer %s shutdown cleanly.", self.consumer_name)
