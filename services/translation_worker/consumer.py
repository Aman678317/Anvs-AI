"""Redis Streams NMT Consumer enforcing Invariant #2 (Immutable Lineage)."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from packages.config.settings import settings
from packages.event_schema import (
    STREAM_TRANSCRIPTS,
    STREAM_TRANSLATIONS,
    RedisStreamBus,
    SourceSegmentEvent,
    TranslationSegmentEvent,
    get_stream_key,
)
from packages.language_registry import normalize_code
from services.translation_worker.context import ContextWindowBuffer
from services.translation_worker.engine import BaseNMTEngine, create_nmt_engine

logger = logging.getLogger(__name__)


class NMTConsumer:
    """Consumes SourceSegmentEvents, translates into active target languages, and publishes."""

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        engine: BaseNMTEngine | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
        target_languages: list[str] | None = None,
        context_window: ContextWindowBuffer | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.engine = engine or create_nmt_engine()
        self.group_name = group_name or settings.nmt_consumer_group
        self.consumer_name = consumer_name or f"nmt-worker-{uuid.uuid4().hex[:8]}"
        self.target_languages = target_languages or settings.nmt_default_target_languages
        self.context_window = context_window or ContextWindowBuffer(
            max_sentences=settings.nmt_context_window_size
        )

        # Operational metrics
        self.metrics = {
            "messages_consumed": 0,
            "translations_emitted": 0,
            "errors_count": 0,
            "total_latency_ms": 0,
        }

    async def setup(self, meeting_id: str) -> None:
        """Initializes consumer group on the transcripts stream for a meeting."""
        stream_key = get_stream_key(meeting_id, STREAM_TRANSCRIPTS)
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
    ) -> list[TranslationSegmentEvent]:
        """Processes a single SourceSegmentEvent and emits TranslationSegmentEvents."""
        emitted_events: list[TranslationSegmentEvent] = []

        try:
            # 1. Parse SourceSegmentEvent
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = json.loads(str(raw_payload))

            source_event = SourceSegmentEvent.model_validate(payload_dict)

            # Invariant #2: Exact source_segment_id lineage preservation
            source_lineage_id = source_event.source_segment_id

            # Filter active target languages (exclude identical source-target)
            src_norm = normalize_code(source_event.language)
            targets = [
                tgt for tgt in self.target_languages if normalize_code(tgt) != src_norm
            ]

            if not targets:
                # No translation needed for same language
                await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
                self.metrics["messages_consumed"] += 1
                return []

            # 2. Retrieve preceding discourse context for speaker
            context = self.context_window.get_context(
                meeting_id=meeting_id,
                participant_id=source_event.participant_id,
            )

            # 3. Translate across target languages
            translations = await self.engine.translate_batch(
                text=source_event.text,
                source_lang=source_event.language,
                target_languages=targets,
                context=context,
            )

            # 4. Emit TranslationSegmentEvent per target language
            translations_stream = get_stream_key(meeting_id, STREAM_TRANSLATIONS)

            for res in translations:
                event = TranslationSegmentEvent(
                    event_id=f"trans_evt_{uuid.uuid4()}",
                    timestamp_ms=int(time.time() * 1000),
                    meeting_id=meeting_id,
                    tenant_id=source_event.tenant_id,
                    source_segment_id=source_lineage_id,
                    source_language=res.source_language,
                    target_language=res.target_language,
                    translated_text=res.translated_text,
                    is_final=source_event.is_final,
                    latency_ms=res.latency_ms,
                )

                await self.stream_bus.publish(stream=translations_stream, event=event)
                emitted_events.append(event)
                self.metrics["translations_emitted"] += 1
                self.metrics["total_latency_ms"] += res.latency_ms

            # 5. Update context window if utterance is final
            if source_event.is_final:
                self.context_window.add_utterance(
                    meeting_id=meeting_id,
                    participant_id=source_event.participant_id,
                    text=source_event.text,
                )

            # 6. Acknowledge message
            await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
            self.metrics["messages_consumed"] += 1

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error processing NMT transcript message %s in stream %s: %s",
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
    ) -> list[TranslationSegmentEvent]:
        """Polls Redis Stream once and processes pending transcript messages."""
        stream_key = get_stream_key(meeting_id, STREAM_TRANSCRIPTS)
        raw_events = await self.stream_bus.consume_events(
            stream=stream_key,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            event_class=None,
        )

        all_emitted: list[TranslationSegmentEvent] = []
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
            "Starting NMT consumer %s for meeting %s (group: %s)",
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
                logger.error("Unexpected error in NMT consumer loop: %s", exc)
                await asyncio.sleep(0.5)

        logger.info("NMT consumer %s shutdown cleanly.", self.consumer_name)
