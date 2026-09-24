"""Redis Streams STT Consumer enforcing Invariant #2 (Lineage Preservation)."""

import asyncio
import base64
import json
import logging
import time
import uuid
from typing import Any

import numpy as np

from packages.audio.framing import pcm_s16le_to_float32
from packages.config.settings import settings
from packages.event_schema import (
    STREAM_AUDIO,
    STREAM_TRANSCRIPTS,
    RedisStreamBus,
    SourceSegmentEvent,
    get_stream_key,
)
from services.stt_worker.engine import BaseSTTEngine, create_stt_engine
from services.stt_worker.language import to_iso639_3

logger = logging.getLogger(__name__)


class STTConsumer:
    """Consumes audio segments from Redis Streams and publishes speech transcripts."""

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        engine: BaseSTTEngine | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.engine = engine or create_stt_engine()
        self.group_name = group_name or settings.stt_consumer_group
        self.consumer_name = consumer_name or f"stt-worker-{uuid.uuid4().hex[:8]}"

        # Operational metrics
        self.metrics = {
            "messages_consumed": 0,
            "partials_emitted": 0,
            "finals_emitted": 0,
            "errors_count": 0,
            "total_audio_duration_ms": 0,
        }

    async def setup(self, meeting_id: str) -> None:
        """Initializes consumer groups for audio streams of a given meeting."""
        stream_key = get_stream_key(meeting_id, STREAM_AUDIO)
        await self.stream_bus.create_consumer_group(
            stream=stream_key,
            group_name=self.group_name,
        )

    def _extract_audio_samples(self, audio_uri: str) -> tuple[np.ndarray, int]:
        """Decodes audio URI into float32 numpy samples."""
        if audio_uri.startswith("base64://"):
            b64_payload = audio_uri[len("base64://") :]
            pcm_bytes = base64.b64decode(b64_payload)
            samples = pcm_s16le_to_float32(pcm_bytes)
            return samples, len(pcm_bytes)

        raise ValueError(f"Unsupported audio URI scheme: {audio_uri}")

    def _parse_source_metadata(
        self,
        source_segment_id: str,
        payload_dict: dict[str, Any],
        meeting_id: str,
    ) -> tuple[str, str, int]:
        """Extracts participant_id, session_id, and start_offset_ms."""
        participant_id = payload_dict.get("participant_id")
        session_id = payload_dict.get("session_id") or f"session_{meeting_id}"
        start_offset_ms = 0

        # Pattern: src_{participant_id}_{start_ms}
        if source_segment_id.startswith("src_"):
            parts = source_segment_id.split("_")
            if len(parts) >= 3:
                if not participant_id:
                    participant_id = parts[1]
                try:
                    start_offset_ms = int(parts[2])
                except ValueError:
                    start_offset_ms = 0

        if not participant_id:
            participant_id = "participant_unknown"

        return participant_id, session_id, start_offset_ms

    async def process_message(
        self,
        stream_name: str,
        message_id: str,
        raw_payload: str | dict[str, Any],
        meeting_id: str,
    ) -> list[SourceSegmentEvent]:
        """Processes a single audio segment message and emits typed SourceSegmentEvents."""
        emitted_events: list[SourceSegmentEvent] = []

        try:
            # 1. Parse payload into dict
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = json.loads(str(raw_payload))

            # Validate or extract AudioSegmentEvent fields
            audio_uri = payload_dict.get("audio_uri")
            if not audio_uri:
                raise ValueError("Missing 'audio_uri' in audio segment payload")

            source_segment_id = payload_dict.get("source_segment_id")
            if not source_segment_id:
                raise ValueError("Missing 'source_segment_id' in audio segment payload")

            tenant_id = payload_dict.get("tenant_id", "default")
            sample_rate = int(payload_dict.get("sample_rate", 16000))
            raw_lang = payload_dict.get("target_language") or payload_dict.get("language", "eng")
            language = to_iso639_3(raw_lang)

            participant_id, session_id, start_offset_ms = self._parse_source_metadata(
                source_segment_id=source_segment_id,
                payload_dict=payload_dict,
                meeting_id=meeting_id,
            )

            incoming_event_id = payload_dict.get("event_id")
            correlation_id = (
                payload_dict.get("correlation_id") or f"corr_{meeting_id}_{source_segment_id}"
            )
            incoming_hop_count = int(payload_dict.get("hop_count", 0))
            incoming_seq = int(payload_dict.get("sequence_number", 0))

            # 2. Decode audio buffer
            audio_samples, _ = self._extract_audio_samples(audio_uri)
            duration_ms = int((len(audio_samples) / max(1, sample_rate)) * 1000)
            self.metrics["total_audio_duration_ms"] += duration_ms

            # 3. Stream through STT engine
            transcripts_stream = get_stream_key(meeting_id, STREAM_TRANSCRIPTS)

            async for stt_res in self.engine.transcribe_stream(
                audio=audio_samples,
                sample_rate=sample_rate,
                language=language,
                start_offset_ms=start_offset_ms,
            ):
                # Invariant #2: Immutable lineage preservation of source_segment_id
                event = SourceSegmentEvent(
                    event_id=f"src_evt_{uuid.uuid4()}",
                    timestamp_ms=int(time.time() * 1000),
                    meeting_id=meeting_id,
                    tenant_id=tenant_id,
                    session_id=session_id,
                    participant_id=participant_id,
                    source_segment_id=source_segment_id,
                    language=stt_res.language,
                    text=stt_res.text,
                    is_final=stt_res.is_final,
                    start_ms=stt_res.start_ms,
                    end_ms=stt_res.end_ms,
                    confidence=stt_res.confidence,
                    speaker_tag=None,
                    correlation_id=correlation_id,
                    causation_id=incoming_event_id,
                    parent_event_id=incoming_event_id,
                    sequence_number=incoming_seq + 1,
                    hop_count=incoming_hop_count + 1,
                )

                await self.stream_bus.publish(stream=transcripts_stream, event=event)
                emitted_events.append(event)

                if stt_res.is_final:
                    self.metrics["finals_emitted"] += 1
                else:
                    self.metrics["partials_emitted"] += 1

            # 4. Acknowledge successfully processed message
            await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
            self.metrics["messages_consumed"] += 1

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error processing STT audio message %s in stream %s: %s",
                message_id,
                stream_name,
                exc,
                exc_info=True,
            )
            # Route poison pill to Dead Letter Queue (DLQ)
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

        return emitted_events

    async def poll_and_process(
        self,
        meeting_id: str,
        count: int = 10,
        block_ms: int = 500,
    ) -> list[SourceSegmentEvent]:
        """Polls Redis Stream once and processes pending audio messages."""
        stream_key = get_stream_key(meeting_id, STREAM_AUDIO)
        raw_events = await self.stream_bus.consume_events(
            stream=stream_key,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            event_class=None,
        )

        all_emitted: list[SourceSegmentEvent] = []
        for message_id, payload in raw_events:
            events = await self.process_message(
                stream_name=stream_key,
                message_id=message_id,
                raw_payload=payload,
                meeting_id=meeting_id,
            )
            all_emitted.extend(events)

        return all_emitted

    async def run(
        self,
        meeting_id: str,
        stop_event: asyncio.Event | None = None,
        count: int = 10,
        block_ms: int = 1000,
    ) -> None:
        """Runs the continuous consumer loop until stop_event is set."""
        await self.setup(meeting_id)
        logger.info(
            "Starting STT consumer %s for meeting %s (group: %s)",
            self.consumer_name,
            meeting_id,
            self.group_name,
        )

        while stop_event is None or not stop_event.is_set():
            try:
                await self.poll_and_process(
                    meeting_id=meeting_id,
                    count=count,
                    block_ms=block_ms,
                )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in STT consumer loop: %s", exc)
                await asyncio.sleep(0.5)

        logger.info("STT consumer %s shutdown cleanly.", self.consumer_name)
