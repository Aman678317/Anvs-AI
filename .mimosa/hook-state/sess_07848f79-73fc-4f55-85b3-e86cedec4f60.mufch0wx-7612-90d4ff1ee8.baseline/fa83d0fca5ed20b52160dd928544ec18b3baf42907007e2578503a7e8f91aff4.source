"""Unit tests for the Redis Streams Bus Manager."""

from unittest.mock import AsyncMock

import pytest
from redis.exceptions import ResponseError

from packages.event_schema import (
    STREAM_AUDIO,
    STREAM_DLQ,
    STREAM_TRANSCRIPTS,
    RedisStreamBus,
    SourceSegmentEvent,
    get_stream_key,
)


@pytest.mark.unit
def test_stream_key_generation() -> None:
    assert get_stream_key("meet-456", STREAM_AUDIO) == "events:meeting:meet-456:audio"
    assert get_stream_key("meet-456", STREAM_TRANSCRIPTS) == "events:meeting:meet-456:transcripts"
    assert get_stream_key("meet-456", STREAM_DLQ) == "events:meeting:meet-456:dlq"


@pytest.mark.unit
def test_client_not_connected_raises() -> None:
    bus = RedisStreamBus(redis_url="redis://localhost:6379/0")
    with pytest.raises(RuntimeError, match="not connected"):
        _ = bus.client


@pytest.mark.unit
@pytest.mark.asyncio
async def test_publish_event_capped() -> None:
    mock_client = AsyncMock()
    mock_client.xadd.return_value = "1710000000000-0"

    bus = RedisStreamBus(client=mock_client)
    event = SourceSegmentEvent(
        event_id="evt-1",
        timestamp_ms=1710000000000,
        meeting_id="meet-456",
        session_id="sess-1",
        participant_id="user-1",
        source_segment_id="src-1",
        language="eng",
        text="Hello world",
        is_final=True,
        start_ms=0,
        end_ms=1000,
        confidence=0.95,
    )

    stream_name = get_stream_key("meet-456", STREAM_TRANSCRIPTS)
    msg_id = await bus.publish(stream_name, event, max_len=5000)

    assert msg_id == "1710000000000-0"
    mock_client.xadd.assert_awaited_once()
    call_args = mock_client.xadd.call_args
    assert call_args.kwargs["name"] == stream_name
    assert call_args.kwargs["maxlen"] == 5000
    assert call_args.kwargs["approximate"] is True
    assert "payload" in call_args.kwargs["fields"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_consumer_group_idempotent() -> None:
    mock_client = AsyncMock()
    bus = RedisStreamBus(client=mock_client)

    # First creation succeeds
    mock_client.xgroup_create.return_value = "OK"
    created = await bus.create_consumer_group("stream-1", "group-1")
    assert created is True

    # Second creation raises BUSYGROUP (already exists)
    mock_client.xgroup_create.side_effect = ResponseError(
        "BUSYGROUP Consumer Group name already exists"
    )
    created_again = await bus.create_consumer_group("stream-1", "group-1")
    assert created_again is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_events_typed() -> None:
    sample_event = SourceSegmentEvent(
        event_id="evt-1",
        timestamp_ms=1710000000000,
        meeting_id="meet-456",
        session_id="sess-1",
        participant_id="user-1",
        source_segment_id="src-1",
        language="eng",
        text="Streaming STT test",
        is_final=True,
        start_ms=0,
        end_ms=1200,
        confidence=0.98,
    )

    mock_client = AsyncMock()
    mock_client.xreadgroup.return_value = [
        (
            "events:meeting:meet-456:transcripts",
            [("1710000000000-0", {"payload": sample_event.model_dump_json()})],
        )
    ]

    bus = RedisStreamBus(client=mock_client)
    consumed = await bus.consume_events(
        stream="events:meeting:meet-456:transcripts",
        group_name="translation_workers",
        consumer_name="worker-1",
        event_class=SourceSegmentEvent,
    )

    assert len(consumed) == 1
    msg_id, event = consumed[0]
    assert msg_id == "1710000000000-0"
    assert isinstance(event, SourceSegmentEvent)
    assert event.source_segment_id == "src-1"
    assert event.text == "Streaming STT test"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_consume_events_raw_dict() -> None:
    mock_client = AsyncMock()
    mock_client.xreadgroup.return_value = [
        (
            "events:meeting:meet-456:transcripts",
            [("1710000000000-1", {"payload": '{"key": "value"}'})],
        )
    ]

    bus = RedisStreamBus(client=mock_client)
    consumed = await bus.consume_events(
        stream="events:meeting:meet-456:transcripts",
        group_name="generic_group",
        consumer_name="worker-2",
        event_class=None,
    )

    assert len(consumed) == 1
    msg_id, data = consumed[0]
    assert msg_id == "1710000000000-1"
    assert isinstance(data, dict)
    assert data["key"] == "value"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_ack_event() -> None:
    mock_client = AsyncMock()
    mock_client.xack.return_value = 1

    bus = RedisStreamBus(client=mock_client)
    ack_count = await bus.ack_event("stream-1", "group-1", "1710000000000-0")

    assert ack_count == 1
    mock_client.xack.assert_awaited_once_with("stream-1", "group-1", "1710000000000-0")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_send_to_dlq() -> None:
    mock_client = AsyncMock()
    mock_client.xadd.return_value = "dlq-msg-id-123"
    mock_client.xack.return_value = 1

    bus = RedisStreamBus(client=mock_client)
    dlq_id = await bus.send_to_dlq(
        meeting_id="meet-456",
        original_stream="events:meeting:meet-456:transcripts",
        group_name="translation_workers",
        message_id="bad-msg-1",
        raw_payload="poisoned content",
        error_reason="JSONDecodeError: invalid format",
        retry_count=3,
    )

    assert dlq_id == "dlq-msg-id-123"
    mock_client.xadd.assert_awaited_once()
    mock_client.xack.assert_awaited_once_with(
        "events:meeting:meet-456:transcripts", "translation_workers", "bad-msg-1"
    )
