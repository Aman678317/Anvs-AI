"""Pipeline Orchestrator & End-to-End Stream Coordinator (PR-13).

Coordinates stream handoffs across STT, NMT, and TTS workers with automated
backpressure shedding, worker crash recovery (<3s SLA), and graceful degradation.
Enforces explicit stream trimming (XTRIM) to cap Redis memory growth (P1-06).
"""

import logging
import time
from typing import Any

from packages.config.settings import settings
from packages.contracts import (
    DegradationTier,
    PipelineStatusResponse,
    WorkerHealthStatus,
    WorkerHeartbeatPayload,
)
from packages.event_schema import (
    STREAM_ASSISTANT,
    STREAM_AUDIO,
    STREAM_DIARIZATION,
    STREAM_DLQ,
    STREAM_SYNTHESIZED_AUDIO,
    STREAM_TRANSCRIPTS,
    STREAM_TRANSLATIONS,
    RedisStreamBus,
    get_stream_key,
)
from services.orchestrator.backpressure import BackpressureController
from services.orchestrator.dlq_retry import DLQRetryManager
from services.orchestrator.heartbeat import WorkerHealthMonitor

logger = logging.getLogger(__name__)


class PipelineOrchestrator:
    """Master pipeline orchestrator managing flow control, health, memory trimming, and failover recovery."""

    def __init__(
        self,
        stream_bus: RedisStreamBus,
        backpressure: BackpressureController | None = None,
        health_monitor: WorkerHealthMonitor | None = None,
        dlq_manager: DLQRetryManager | None = None,
        stream_maxlen: int | None = None,
    ) -> None:
        self.stream_bus = stream_bus
        self.backpressure = backpressure or BackpressureController()
        self.health_monitor = health_monitor or WorkerHealthMonitor()
        self.dlq_manager = dlq_manager or DLQRetryManager(stream_bus)
        self.stream_maxlen = stream_maxlen or settings.orchestrator_stream_maxlen

        self._start_time = time.time()
        self._active_pipelines: set[str] = set()

    async def initialize_meeting_pipeline(self, meeting_id: str) -> None:
        """Provision consumer groups, trimming policies, and monitoring channels for a new meeting."""
        self._active_pipelines.add(meeting_id)
        await self.dlq_manager.setup(meeting_id)
        # Apply initial stream trimming bounds to guarantee bounded Redis memory (P1-06)
        await self.trim_meeting_streams(meeting_id)

    def record_worker_heartbeat(self, payload: WorkerHeartbeatPayload) -> None:
        """Record liveness heartbeat from any AI worker in the fleet."""
        self.health_monitor.record_heartbeat(payload)

    def get_meeting_stream_keys(self, meeting_id: str) -> dict[str, str]:
        """Returns standard stream key mapping for all event channels of a meeting."""
        return {
            "audio": get_stream_key(meeting_id, STREAM_AUDIO),
            "transcripts": get_stream_key(meeting_id, STREAM_TRANSCRIPTS),
            "translations": get_stream_key(meeting_id, STREAM_TRANSLATIONS),
            "synthesized_audio": get_stream_key(meeting_id, STREAM_SYNTHESIZED_AUDIO),
            "diarization": get_stream_key(meeting_id, STREAM_DIARIZATION),
            "assistant": get_stream_key(meeting_id, STREAM_ASSISTANT),
            "dlq": get_stream_key(meeting_id, STREAM_DLQ),
        }

    async def trim_meeting_streams(
        self,
        meeting_id: str,
        max_len: int | None = None,
    ) -> dict[str, int]:
        """Trims all event streams for a meeting using XTRIM to cap memory growth (P1-06).

        Returns:
            Dictionary mapping stream name to number of trimmed entries.
        """
        target_maxlen = max_len or self.stream_maxlen
        streams = self.get_meeting_stream_keys(meeting_id)
        trim_results: dict[str, int] = {}

        for name, stream_key in streams.items():
            try:
                trimmed = await self.stream_bus.trim_stream(
                    stream=stream_key,
                    max_len=target_maxlen,
                    approximate=True,
                )
                trim_results[name] = trimmed
            except Exception as exc:
                logger.debug("Stream trimming skipped for %s: %s", stream_key, exc)
                trim_results[name] = 0

        logger.debug(
            "Trimmed streams for meeting %s (maxlen=%d): %s",
            meeting_id,
            target_maxlen,
            trim_results,
        )
        return trim_results

    async def get_stream_depths(self, meeting_id: str) -> dict[str, int]:
        """Fetch current message queue length across all active media and text streams."""
        streams = self.get_meeting_stream_keys(meeting_id)

        depths: dict[str, int] = {}
        for name, stream_key in streams.items():
            try:
                depths[name] = await self.stream_bus.get_stream_length(stream_key)
            except Exception:
                depths[name] = 0

        return depths

    async def update_pipeline_state(
        self,
        meeting_id: str,
        now: float | None = None,
    ) -> DegradationTier:
        """Evaluate worker liveness and queue depths to determine active degradation tier.

        DoD Rule: If TTS workers are DEAD, gracefully degrade to CRITICAL_LOAD (Captions Only).
        If queue depth exceeds thresholds, elevate tier immediately.
        """
        depths = await self.get_stream_depths(meeting_id)
        liveness = self.health_monitor.evaluate_liveness(now=now)
        aggregate_health = self.health_monitor.get_aggregate_health_by_type(liveness)

        force_tier: DegradationTier | None = None

        # If TTS is dead, degrade to Captions Only (CRITICAL_LOAD)
        if aggregate_health.get("tts") == WorkerHealthStatus.DEAD:
            logger.warning(
                "TTS Worker fleet DEAD for meeting %s! Activating Captions Only degradation.",
                meeting_id,
            )
            force_tier = DegradationTier.CRITICAL_LOAD

        # If STT or NMT is dead, enter EMERGENCY tier (original audio pass-through)
        if (
            aggregate_health.get("stt") == WorkerHealthStatus.DEAD
            or aggregate_health.get("nmt") == WorkerHealthStatus.DEAD
        ):
            logger.critical(
                "Core Speech/Translation fleet DEAD for meeting %s! Entering EMERGENCY pass-through.",
                meeting_id,
            )
            force_tier = DegradationTier.EMERGENCY

        return self.backpressure.evaluate_queue_depths(depths, force_tier=force_tier)

    def should_synthesize_speech(self, tier: DegradationTier | None = None) -> bool:
        """Determine if TTS voice synthesis should execute or be bypassed for Captions Only."""
        active_tier = tier or self.backpressure.current_tier
        # Captions Only mode in CRITICAL_LOAD or EMERGENCY
        return active_tier in (DegradationTier.NORMAL, DegradationTier.HIGH_LOAD)

    async def recover_stuck_messages(
        self,
        meeting_id: str,
        stream_type: str,
        group_name: str,
        consumer_name: str,
        min_idle_ms: int = 3000,
        count: int = 20,
    ) -> list[Any]:
        """Claim abandoned pending messages from crashed workers within 3s SLA."""
        stream_key = get_stream_key(meeting_id, stream_type)
        claimed = await self.stream_bus.claim_pending_events(
            stream=stream_key,
            group_name=group_name,
            consumer_name=consumer_name,
            min_idle_time_ms=min_idle_ms,
            count=count,
        )
        if claimed:
            logger.info(
                "Claimed %d abandoned messages from stream %s for recovery",
                len(claimed),
                stream_key,
            )
        return claimed

    async def get_pipeline_status(self, meeting_id: str) -> PipelineStatusResponse:
        """Build status report for meeting pipeline flow control and health."""
        depths = await self.get_stream_depths(meeting_id)
        liveness = self.health_monitor.evaluate_liveness()
        uptime = time.time() - self._start_time

        return PipelineStatusResponse(
            meeting_id=meeting_id,
            current_tier=self.backpressure.current_tier,
            active_workers=liveness,
            queue_depths=depths,
            dropped_partials_count=self.backpressure.dropped_partials_count,
            uptime_seconds=round(uptime, 2),
        )
