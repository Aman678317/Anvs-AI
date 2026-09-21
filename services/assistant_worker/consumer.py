"""Redis Streams Assistant Consumer enforcing Invariant #2 (Citation Lineage)."""

import asyncio
import json
import logging
import time
import uuid
from typing import Any

from packages.config.settings import settings
from packages.event_schema import (
    STREAM_ASSISTANT,
    STREAM_TRANSCRIPTS,
    AssistantQueryEvent,
    AssistantResponseEvent,
    RedisStreamBus,
    SourceSegmentEvent,
    get_stream_key,
)
from services.assistant_worker.engine import BaseAssistantEngine, create_assistant_engine
from services.assistant_worker.types import IndexedSegment
from services.assistant_worker.vector_store import TranscriptVectorStore

logger = logging.getLogger(__name__)


class AssistantConsumer:
    """Consumes transcripts for RAG indexing and queries for grounded response generation."""

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        engine: BaseAssistantEngine | None = None,
        vector_store: TranscriptVectorStore | None = None,
        group_name: str | None = None,
        consumer_name: str | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.engine = engine or create_assistant_engine()
        self.vector_store = vector_store or TranscriptVectorStore()
        self.group_name = group_name or settings.assistant_consumer_group
        self.consumer_name = consumer_name or f"assistant-worker-{uuid.uuid4().hex[:8]}"

        # Operational metrics
        self.metrics = {
            "transcripts_indexed": 0,
            "queries_processed": 0,
            "responses_emitted": 0,
            "action_items_extracted": 0,
            "errors_count": 0,
        }

    async def setup(self, meeting_id: str) -> None:
        """Initializes consumer groups on transcripts and assistant streams."""
        transcripts_stream = get_stream_key(meeting_id, STREAM_TRANSCRIPTS)
        assistant_stream = get_stream_key(meeting_id, STREAM_ASSISTANT)

        await self.stream_bus.create_consumer_group(
            stream=transcripts_stream,
            group_name=self.group_name,
        )
        await self.stream_bus.create_consumer_group(
            stream=assistant_stream,
            group_name=self.group_name,
        )

    async def process_transcript_message(
        self,
        stream_name: str,
        message_id: str,
        raw_payload: str | dict[str, Any],
        meeting_id: str,
    ) -> IndexedSegment | None:
        """Indexes a final SourceSegmentEvent into the localized vector store."""
        try:
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = json.loads(str(raw_payload))

            event = SourceSegmentEvent.model_validate(payload_dict)

            # Only index completed final transcript utterances for RAG
            if not event.is_final or not event.text.strip():
                await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
                return None

            # Compute dense 1536-dim vector embedding
            embedding = self.engine.embed_text(event.text)
            indexed_seg = IndexedSegment(
                source_segment_id=event.source_segment_id,
                text=event.text,
                speaker_name=event.speaker_tag or event.participant_id,
                embedding=embedding,
                timestamp_ms=event.timestamp_ms,
                meeting_id=meeting_id,
                tenant_id=event.tenant_id,
            )

            self.vector_store.add_segment(indexed_seg)
            self.metrics["transcripts_indexed"] += 1

            await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
            return indexed_seg

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error indexing transcript segment %s in %s: %s",
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
            return None

    async def process_query_message(
        self,
        stream_name: str,
        message_id: str,
        raw_payload: str | dict[str, Any],
        meeting_id: str,
    ) -> AssistantResponseEvent | None:
        """Processes an AssistantQueryEvent and emits an AssistantResponseEvent with citations."""
        try:
            if isinstance(raw_payload, str):
                payload_dict = json.loads(raw_payload)
            elif isinstance(raw_payload, dict):
                payload_dict = raw_payload
            else:
                payload_dict = json.loads(str(raw_payload))

            query_event = AssistantQueryEvent.model_validate(payload_dict)

            # 1. Embed query text
            query_emb = self.engine.embed_text(query_event.question)

            # 2. Semantic search over meeting transcript segments
            retrieved = self.vector_store.similarity_search(
                query_embedding=query_emb,
                meeting_id=meeting_id,
                top_k=settings.assistant_top_k,
                threshold=settings.assistant_similarity_threshold,
            )

            # 3. Formulate grounded answer with Invariant #2 citation lineage
            answer_res = await self.engine.answer_query(
                query=query_event.question,
                retrieved_segments=retrieved,
                query_id=query_event.query_id,
            )

            # 4. Construct and publish AssistantResponseEvent
            assistant_stream = get_stream_key(meeting_id, STREAM_ASSISTANT)
            response_event = AssistantResponseEvent(
                event_id=f"asst_resp_{uuid.uuid4()}",
                timestamp_ms=int(time.time() * 1000),
                meeting_id=meeting_id,
                tenant_id=query_event.tenant_id,
                query_id=query_event.query_id,
                answer=answer_res.answer,
                citations=answer_res.citations,
                action_items=answer_res.action_items,
            )

            await self.stream_bus.publish(stream=assistant_stream, event=response_event)
            self.metrics["queries_processed"] += 1
            self.metrics["responses_emitted"] += 1
            self.metrics["action_items_extracted"] += len(answer_res.action_items)

            # 5. Acknowledge query message
            await self.stream_bus.ack_event(stream_name, self.group_name, message_id)
            return response_event

        except Exception as exc:
            self.metrics["errors_count"] += 1
            logger.error(
                "Error processing assistant query %s in %s: %s",
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
            return None

    async def poll_transcripts(
        self,
        meeting_id: str,
        count: int = 10,
        block_ms: int = 500,
    ) -> list[IndexedSegment]:
        """Polls transcripts stream and indexes pending segments."""
        stream_key = get_stream_key(meeting_id, STREAM_TRANSCRIPTS)
        raw_events = await self.stream_bus.consume_events(
            stream=stream_key,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            event_class=None,
        )

        indexed: list[IndexedSegment] = []
        for message_id, payload in raw_events:
            seg = await self.process_transcript_message(
                stream_name=stream_key,
                message_id=message_id,
                raw_payload=payload,
                meeting_id=meeting_id,
            )
            if seg is not None:
                indexed.append(seg)
        return indexed

    async def poll_queries(
        self,
        meeting_id: str,
        count: int = 10,
        block_ms: int = 500,
    ) -> list[AssistantResponseEvent]:
        """Polls assistant queries stream and responds to pending queries."""
        stream_key = get_stream_key(meeting_id, STREAM_ASSISTANT)
        raw_events = await self.stream_bus.consume_events(
            stream=stream_key,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=count,
            block_ms=block_ms,
            event_class=None,
        )

        responses: list[AssistantResponseEvent] = []
        for message_id, payload in raw_events:
            # Skip responses already published to the stream
            if isinstance(payload, dict) and "answer" in payload:
                await self.stream_bus.ack_event(stream_key, self.group_name, message_id)
                continue

            resp = await self.process_query_message(
                stream_name=stream_key,
                message_id=message_id,
                raw_payload=payload,
                meeting_id=meeting_id,
            )
            if resp is not None:
                responses.append(resp)
        return responses

    async def run(
        self,
        meeting_id: str,
        stop_event: asyncio.Event | None = None,
        count: int = 10,
        block_ms: int = 1000,
    ) -> None:
        """Runs the continuous assistant consumer loop until stop_event is set."""
        await self.setup(meeting_id)
        logger.info(
            "Starting assistant consumer %s for meeting %s (group: %s)",
            self.consumer_name,
            meeting_id,
            self.group_name,
        )

        while stop_event is None or not stop_event.is_set():
            try:
                await self.poll_transcripts(meeting_id, count=count, block_ms=block_ms // 2)
                await self.poll_queries(meeting_id, count=count, block_ms=block_ms // 2)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Unexpected error in assistant consumer loop: %s", exc)
                await asyncio.sleep(0.5)

        logger.info("Assistant consumer %s shutdown cleanly.", self.consumer_name)
