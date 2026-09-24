"""Dead Letter Queue (DLQ) Recovery & Exponential Backoff Retry Engine (PR-13).

Processes failing event packets, applies exponential backoff retries,
and securely quarantines poisoned packets to prevent infinite retry loops (Invariant #4).
"""

import json
import logging

from packages.config.settings import settings
from packages.event_schema import (
    STREAM_DLQ,
    DeadLetterEvent,
    RedisStreamBus,
    get_stream_key,
)

logger = logging.getLogger(__name__)


class DLQRetryOutcome:
    """Status outcomes for a DLQ event processing attempt."""

    RETRIED = "RETRIED"
    QUARANTINED = "QUARANTINED"
    SKIPPED = "SKIPPED"


class DLQRetryManager:
    """Manages Dead Letter Queue consumption, retry exponential backoff, and poison quarantine."""

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        max_retries: int | None = None,
        base_backoff_sec: float = 0.5,
        consumer_group: str = "orchestrator-dlq-group",
        consumer_name: str = "dlq-retry-manager",
    ) -> None:
        self.stream_bus = stream_bus
        self.max_retries = max_retries or settings.orchestrator_dlq_max_retries
        self.base_backoff_sec = base_backoff_sec
        self.consumer_group = consumer_group
        self.consumer_name = consumer_name

        self.retried_count = 0
        self.quarantined_count = 0

    def get_metrics(self) -> dict[str, int]:
        """Returns DLQ retry and quarantine telemetry metrics."""
        return {
            "retried_count": self.retried_count,
            "quarantined_count": self.quarantined_count,
        }

    async def setup(self, meeting_id: str) -> None:
        """Initialize consumer group on meeting's DLQ stream."""
        dlq_stream = get_stream_key(meeting_id, STREAM_DLQ)
        await self.stream_bus.create_consumer_group(
            stream=dlq_stream,
            group_name=self.consumer_group,
            start_id="0",
        )

    def calculate_backoff(self, retry_count: int) -> float:
        """Calculate exponential backoff delay in seconds."""
        return self.base_backoff_sec * (2**retry_count)

    async def process_dlq_event(
        self,
        dlq_event: DeadLetterEvent,
        dlq_message_id: str,
        dlq_stream: str,
    ) -> str:
        """Process a single DLQ entry with retry backoff or terminal quarantine."""
        if dlq_event.retry_count < self.max_retries:
            next_retry = dlq_event.retry_count + 1
            backoff = self.calculate_backoff(dlq_event.retry_count)

            logger.warning(
                "Retrying DLQ event %s to %s (attempt %d/%d, backoff=%.2fs, reason: %s)",
                dlq_event.failed_event_id,
                dlq_event.original_stream,
                next_retry,
                self.max_retries,
                backoff,
                dlq_event.error_reason,
            )

            # Re-publish to original stream with incremented retry count in payload if JSON
            try:
                payload_dict = json.loads(dlq_event.raw_payload)
                payload_dict["retry_count"] = next_retry
                new_payload = json.dumps(payload_dict)
            except Exception:
                new_payload = dlq_event.raw_payload

            await self.stream_bus.client.xadd(
                name=dlq_event.original_stream,
                fields={"payload": new_payload},
            )
            # Acknowledge DLQ event to remove from pending
            await self.stream_bus.ack_event(dlq_stream, self.consumer_group, dlq_message_id)
            self.retried_count += 1
            return DLQRetryOutcome.RETRIED

        # Exceeded max retries: Terminal Poison Pill Quarantine
        logger.critical(
            "POISON PILL QUARANTINE: Event %s permanently failed after %d retries. Reason: %s",
            dlq_event.failed_event_id,
            dlq_event.retry_count,
            dlq_event.error_reason,
        )
        # ACK in DLQ so it does not loop forever (Invariant #4)
        await self.stream_bus.ack_event(dlq_stream, self.consumer_group, dlq_message_id)
        self.quarantined_count += 1
        return DLQRetryOutcome.QUARANTINED

    async def poll_and_retry(
        self,
        meeting_id: str,
        batch_size: int = 10,
    ) -> list[str]:
        """Poll DLQ stream for a meeting and execute retry / quarantine logic."""
        dlq_stream = get_stream_key(meeting_id, STREAM_DLQ)
        messages = await self.stream_bus.consume_events(
            stream=dlq_stream,
            group_name=self.consumer_group,
            consumer_name=self.consumer_name,
            count=batch_size,
            block_ms=500,
            event_class=DeadLetterEvent,
        )

        outcomes: list[str] = []
        for msg_id, event in messages:
            if isinstance(event, DeadLetterEvent):
                outcome = await self.process_dlq_event(event, msg_id, dlq_stream)
                outcomes.append(outcome)

        return outcomes
