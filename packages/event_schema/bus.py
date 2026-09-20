"""Redis Streams Bus Manager adhering to Documents 08, 12, and 14."""

import json
import time
import uuid
from typing import Any, TypeVar

import redis.asyncio as aioredis
from redis.asyncio import Redis
from redis.exceptions import ResponseError

from packages.config.settings import settings

from .events import BaseEvent, DeadLetterEvent

T = TypeVar("T", bound=BaseEvent)

# Stream Type Constants
STREAM_AUDIO = "audio"
STREAM_TRANSCRIPTS = "transcripts"
STREAM_TRANSLATIONS = "translations"
STREAM_SYNTHESIZED_AUDIO = "synthesized_audio"
STREAM_DIARIZATION = "diarization"
STREAM_ASSISTANT = "assistant"
STREAM_ROOM_STATE = "room_state"
STREAM_DLQ = "dlq"


def get_stream_key(meeting_id: str, stream_type: str) -> str:
    """Generate standardized Redis stream key for a meeting event channel."""
    return f"events:meeting:{meeting_id}:{stream_type}"


class RedisStreamBus:
    """High-performance Redis Streams bus with consumer groups and DLQ isolation."""

    def __init__(
        self,
        redis_url: str | None = None,
        client: Redis | None = None,
    ) -> None:
        self.redis_url = redis_url or settings.redis_url
        self._client: Redis | None = client
        self._owns_client = client is None

    async def connect(self) -> Redis:
        """Establish or return existing connection to Redis."""
        if self._client is None:
            self._client = aioredis.from_url(
                self.redis_url,
                decode_responses=True,
            )
        return self._client

    async def disconnect(self) -> None:
        """Close connection to Redis if owned by this instance."""
        if self._client is not None and self._owns_client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "RedisStreamBus":
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.disconnect()

    @property
    def client(self) -> Redis:
        """Return active Redis client or raise RuntimeError."""
        if self._client is None:
            raise RuntimeError("RedisStreamBus is not connected. Call connect() first.")
        return self._client

    async def publish(
        self,
        stream: str,
        event: BaseEvent,
        max_len: int = 10000,
    ) -> str:
        """Publish a typed event to a Redis stream with capped retention."""
        payload = event.model_dump_json()
        message_id: str = await self.client.xadd(
            name=stream,
            fields={"payload": payload},
            maxlen=max_len,
            approximate=True,
        )
        return message_id

    async def create_consumer_group(
        self,
        stream: str,
        group_name: str,
        start_id: str = "$",
    ) -> bool:
        """Idempotently create a consumer group on a stream.

        Returns True if group was newly created, False if already existed.
        """
        try:
            await self.client.xgroup_create(
                name=stream,
                groupname=group_name,
                id=start_id,
                mkstream=True,
            )
            return True
        except ResponseError as err:
            if "BUSYGROUP" in str(err):
                return False
            raise

    async def consume_events(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
        event_class: type[T] | None = None,
    ) -> list[tuple[str, T | dict[str, Any]]]:
        """Consume messages from a consumer group with optional schema validation."""
        response = await self.client.xreadgroup(
            groupname=group_name,
            consumername=consumer_name,
            streams={stream: ">"},
            count=count,
            block=block_ms,
        )

        if not response:
            return []

        results: list[tuple[str, T | dict[str, Any]]] = []
        for _stream_name, messages in response:
            for message_id, data in messages:
                raw_payload = data.get("payload", "{}")
                if event_class is not None:
                    parsed_event = event_class.model_validate_json(raw_payload)
                    results.append((message_id, parsed_event))
                else:
                    parsed_dict = json.loads(raw_payload)
                    results.append((message_id, parsed_dict))

        return results

    async def ack_event(
        self,
        stream: str,
        group_name: str,
        message_id: str,
    ) -> int:
        """Acknowledge processed message in the consumer group."""
        ack_count: int = await self.client.xack(stream, group_name, message_id)
        return ack_count

    async def claim_pending_events(
        self,
        stream: str,
        group_name: str,
        consumer_name: str,
        min_idle_time_ms: int = 60000,
        count: int = 10,
    ) -> list[Any]:
        """Claim stuck or abandoned messages from pending entries list (PEL)."""
        autoclaim_result = await self.client.xautoclaim(
            name=stream,
            groupname=group_name,
            consumername=consumer_name,
            min_idle_time=min_idle_time_ms,
            start_id="0-0",
            count=count,
        )
        return autoclaim_result[1] if autoclaim_result else []

    async def send_to_dlq(
        self,
        meeting_id: str,
        original_stream: str,
        group_name: str,
        message_id: str,
        raw_payload: str,
        error_reason: str,
        retry_count: int = 0,
    ) -> str:
        """Forward a poisoned event to the Dead Letter Queue (DLQ) and ACK the original message."""
        dlq_stream = get_stream_key(meeting_id, STREAM_DLQ)
        dlq_event = DeadLetterEvent(
            event_id=f"dlq-{uuid.uuid4()}",
            timestamp_ms=int(time.time() * 1000),
            meeting_id=meeting_id,
            failed_event_id=message_id,
            original_stream=original_stream,
            error_reason=error_reason,
            retry_count=retry_count,
            raw_payload=raw_payload,
        )
        dlq_msg_id = await self.publish(dlq_stream, dlq_event)
        await self.ack_event(original_stream, group_name, message_id)
        return dlq_msg_id

    async def get_stream_length(self, stream: str) -> int:
        """Return the current length of a Redis stream."""
        length: int = await self.client.xlen(stream)
        return length
