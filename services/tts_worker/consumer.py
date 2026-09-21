"""Redis Streams TTS Consumer enforcing Invariant #2 and Invariant #3."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from packages.config.settings import settings
from packages.event_schema import (
    STREAM_SYNTHESIZED_AUDIO,
    STREAM_TRANSLATIONS,
    AudioSegmentEvent,
    RedisStreamBus,
    TranslationSegmentEvent,
    get_stream_key,
)
from services.tts_worker.engine import BaseTTSEngine, create_tts_engine

logger = logging.getLogger(__name__)


class TTSConsumer:
    """Consumes TranslationSegmentEvents, synthesizes speech, and publishes AudioSegmentEvents."""

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        engine: BaseTTSEngine | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.engine = engine or create_tts_engine()
        self.group_name = group_name or settings.tts_consumer_group
        self.consumer_name = consumer_name or f"tts-worker-{uuid.uuid4().hex[:8]}"

        # Operational metrics
        self.metrics = {
            "messages_consumed": 0,
            "audio_segments_emitted": 0,
            "errors_count": 0,
            "total_synthesis_ms": 0,
        }

    async def setup(self, meeting_id: str) -> None:
        """Initializes consumer group on the translations stream for a meeting."""
        stream_key = get_stream_key(meeting_id, STREAM_TRANSLATIONS)
        await self.stream_bus.create_consumer_group(
            stream=stream_key,
            group_name=self.group_name,
        )

    async def process_message(
        self,
        stream_name: str,
        message_id: str,
        raw_payload: str | dict[str, Any],
        meeting_id: str,
    ) -> list[AudioSegmentEvent]:
        """Processes a single TranslationSegmentEvent and emits an AudioSegmentEvent."""
        emitted_events: list[AudioSegmentEvent] = []

        try:
            # 1. Parse TranslationSegmentEvent
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = json.loads(str(raw_payload))

            translation_event = TranslationSegmentEvent.model_validate(payload_dict)

            # Invariant #2: Exact source_segment_id lineage preservation
            source_lineage_id = translation_event.source_segment_id

            # Only synthesize completed final translations
            if not translation_event.is_final or not translation_event.translated_text.strip():
                await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
                self.metrics["messages_consumed"] += 1
                return []

            # 2. Synthesize speech audio with 20 kHz ultrasonic watermark
            tts_res = await self.engine.synthesize(
                text=translation_event.translated_text,
                language=translation_event.target_language,
            )

            # 3. Construct AudioSegmentEvent adhering to Invariants #2 and #3
            synth_audio_stream = get_stream_key(meeting_id, STREAM_SYNTHESIZED_AUDIO)
            audio_event = AudioSegmentEvent(
                event_id=f"aud_evt_{uuid.uuid4()}",
                timestamp_ms=int(time.time() * 1000),
                meeting_id=meeting_id,
                tenant_id=translation_event.tenant_id,
                source_segment_id=source_lineage_id,
                target_language=translation_event.target_language,
                audio_uri=tts_res.to_base64_uri(),
                duration_ms=tts_res.duration_ms,
                sample_rate=tts_res.sample_rate,
                watermarked=tts_res.watermarked,
            )

            await self.stream_bus.publish(stream=synth_audio_stream, event=audio_event)
            emitted_events.append(audio_event)

            self.metrics["audio_segments_emitted"] += 1
            self.metrics["total_synthesis_ms"] += tts_res.latency_ms

            # 4. Acknowledge message
            await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
            self.metrics["messages_consumed"] += 1

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error processing TTS translation message %s in stream %s: %s",
                message_id,
                stream_name,
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

        return emitted_events

    async def poll_and_process(
        self,
        meeting_id: str,
        count: int = 10,
        block_ms: int = 500,
    ) -> list[AudioSegmentEvent]:
        """Polls Redis Stream once and processes pending translation messages."""
        stream_key = get_stream_key(meeting_id, STREAM_TRANSLATIONS)
        raw_events = await self.stream_bus.consume_events(
            stream=stream_key,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            event_class=None,
        )

        all_emitted: list[AudioSegmentEvent] = []
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
            "Starting TTS consumer %s for meeting %s (group: %s)",
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
                logger.error("Unexpected error in TTS consumer loop: %s", exc)
                await asyncio.sleep(0.5)

        logger.info("TTS consumer %s shutdown cleanly.", self.consumer_name)
