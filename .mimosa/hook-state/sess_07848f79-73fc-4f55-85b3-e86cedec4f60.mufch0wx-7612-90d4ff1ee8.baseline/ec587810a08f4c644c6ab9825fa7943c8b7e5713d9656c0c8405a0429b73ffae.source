"""Worker Health & Liveness Heartbeat Monitor (PR-13).

Tracks periodic heartbeats from AI worker fleet (STT, NMT, TTS, Diarization, Assistant).
Detects unresponsive or crashed workers within 3.0s SLA and triggers automated failover.
"""

import logging
import time

from packages.config.settings import settings
from packages.contracts import WorkerHealthStatus, WorkerHeartbeatPayload

logger = logging.getLogger(__name__)


class WorkerHealthMonitor:
    """Tracks worker heartbeats and identifies dead/degraded workers within the 3.0s SLA."""

    def __init__(self, timeout_sec: float | None = None) -> None:
        self.timeout_sec = timeout_sec or settings.orchestrator_worker_timeout_sec
        # In-memory worker heartbeat cache: worker_key -> dict of metadata
        self._workers: dict[str, dict[str, float | int | str | None]] = {}

    def get_worker_key(self, worker_type: str, worker_id: str) -> str:
        """Standardized unique identifier for worker instance."""
        return f"{worker_type}:{worker_id}"

    def record_heartbeat(self, payload: WorkerHeartbeatPayload) -> None:
        """Register or refresh heartbeat from a worker instance."""
        key = self.get_worker_key(payload.worker_type, payload.worker_id)
        now = time.time()
        self._workers[key] = {
            "worker_type": payload.worker_type,
            "worker_id": payload.worker_id,
            "last_seen": now,
            "timestamp_ms": payload.timestamp_ms,
            "queue_depth": payload.queue_depth or 0,
            "gpu_utilization_pct": payload.gpu_utilization_pct,
        }

    def evaluate_liveness(
        self,
        now: float | None = None,
        timeout_sec: float | None = None,
    ) -> dict[str, WorkerHealthStatus]:
        """Evaluate status of all registered workers against timeout thresholds.

        - elapsed <= timeout_sec (default 3.0s): HEALTHY
        - timeout_sec < elapsed <= timeout_sec * 2 (e.g. 3.0s - 6.0s): DEGRADED
        - elapsed > timeout_sec * 2: DEAD
        """
        current_time = now if now is not None else time.time()
        effective_timeout = timeout_sec or self.timeout_sec

        statuses: dict[str, WorkerHealthStatus] = {}
        for key, record in self._workers.items():
            last_seen = float(record["last_seen"])  # type: ignore[arg-type]
            elapsed = current_time - last_seen

            if elapsed <= effective_timeout:
                status = WorkerHealthStatus.HEALTHY
            elif elapsed <= (effective_timeout * 2):
                status = WorkerHealthStatus.DEGRADED
                logger.warning("Worker %s is DEGRADED (no heartbeat for %.2fs)", key, elapsed)
            else:
                status = WorkerHealthStatus.DEAD
                logger.error("Worker %s is DEAD (no heartbeat for %.2fs)", key, elapsed)

            statuses[key] = status

        return statuses

    def get_aggregate_health_by_type(
        self,
        liveness: dict[str, WorkerHealthStatus] | None = None,
    ) -> dict[str, WorkerHealthStatus]:
        """Aggregate health status per worker type (stt, nmt, tts, speaker, assistant).

        If any worker of a type is HEALTHY, that type is HEALTHY.
        If all workers of a type are DEAD, that type is DEAD.
        """
        active_liveness = liveness or self.evaluate_liveness()
        type_statuses: dict[str, list[WorkerHealthStatus]] = {}

        for key, status in active_liveness.items():
            w_type = key.split(":")[0]
            type_statuses.setdefault(w_type, []).append(status)

        result: dict[str, WorkerHealthStatus] = {}
        for w_type, statuses in type_statuses.items():
            if any(s == WorkerHealthStatus.HEALTHY for s in statuses):
                result[w_type] = WorkerHealthStatus.HEALTHY
            elif any(s == WorkerHealthStatus.DEGRADED for s in statuses):
                result[w_type] = WorkerHealthStatus.DEGRADED
            else:
                result[w_type] = WorkerHealthStatus.DEAD

        return result

    def clear(self) -> None:
        """Reset registered workers."""
        self._workers.clear()
