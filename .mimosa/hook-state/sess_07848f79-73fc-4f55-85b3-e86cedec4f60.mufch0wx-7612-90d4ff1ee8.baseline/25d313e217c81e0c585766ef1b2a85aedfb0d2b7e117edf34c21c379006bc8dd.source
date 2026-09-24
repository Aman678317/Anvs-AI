"""Dynamic Backpressure Management and Graceful Degradation Engine (PR-13).

Implements real-time stream queue monitoring, partial-segment shedding under load,
and hysteresis-backed tier transitions (Normal -> High Load -> Critical Load -> Emergency).
Guarantees 100% preservation of final committed transcript segments (Invariant DoD).
"""

import logging
import time

from packages.config.settings import settings
from packages.contracts import DegradationTier

logger = logging.getLogger(__name__)


TIER_SEVERITY: dict[DegradationTier, int] = {
    DegradationTier.NORMAL: 0,
    DegradationTier.HIGH_LOAD: 1,
    DegradationTier.CRITICAL_LOAD: 2,
    DegradationTier.EMERGENCY: 3,
}


class BackpressureController:
    """Monitors Redis stream queue depths and manages degradation tier transitions."""

    def __init__(
        self,
        high_threshold: int | None = None,
        critical_threshold: int | None = None,
        cooldown_sec: float | None = None,
    ) -> None:
        self.high_threshold = high_threshold or settings.orchestrator_queue_high_threshold
        self.critical_threshold = (
            critical_threshold or settings.orchestrator_queue_critical_threshold
        )
        self.cooldown_sec = cooldown_sec or settings.orchestrator_cooldown_period_sec

        self._current_tier = DegradationTier.NORMAL
        self._last_transition_time = time.time()
        self._dropped_partials = 0
        self._transitions_count = 0

    @property
    def current_tier(self) -> DegradationTier:
        """Return active pipeline degradation tier."""
        return self._current_tier

    @property
    def dropped_partials_count(self) -> int:
        """Return total non-final speech/translation segments shed under backpressure."""
        return self._dropped_partials

    def should_process_segment(
        self,
        is_final: bool,
        tier: DegradationTier | None = None,
    ) -> bool:
        """Evaluate whether a stream segment should be admitted or shed.

        Invariant DoD: Final committed segments (is_final=True) must NEVER be shed.
        Non-final partial segments (is_final=False) are dropped during HIGH_LOAD or worse.
        """
        if is_final:
            return True

        active_tier = tier or self._current_tier
        if active_tier != DegradationTier.NORMAL:
            self._dropped_partials += 1
            return False

        return True

    def evaluate_queue_depths(
        self,
        queue_depths: dict[str, int],
        force_tier: DegradationTier | None = None,
    ) -> DegradationTier:
        """Evaluate observed queue depths across pipeline streams and update tier with hysteresis.

        Transitions upwards (NORMAL -> HIGH -> CRITICAL) are instantaneous for safety.
        Transitions downwards (CRITICAL -> HIGH -> NORMAL) require cooldown hysteresis
        to prevent oscillating thrash under bursty speech patterns.
        """
        if force_tier is not None:
            if self._current_tier != force_tier:
                self._current_tier = force_tier
                self._last_transition_time = time.time()
                self._transitions_count += 1
            return self._current_tier

        now = time.time()
        max_depth = max(queue_depths.values()) if queue_depths else 0

        target_tier = DegradationTier.NORMAL
        if max_depth >= self.critical_threshold:
            target_tier = DegradationTier.CRITICAL_LOAD
        elif max_depth >= self.high_threshold:
            target_tier = DegradationTier.HIGH_LOAD

        target_weight = TIER_SEVERITY.get(target_tier, 0)
        current_weight = TIER_SEVERITY.get(self._current_tier, 0)

        # Upward degradation is immediate (safety first)
        if target_weight > current_weight:
            logger.warning(
                "Upgrading pipeline backpressure tier: %s -> %s (max_depth=%d)",
                self._current_tier.value,
                target_tier.value,
                max_depth,
            )
            self._current_tier = target_tier
            self._last_transition_time = now
            self._transitions_count += 1
            return self._current_tier

        # Downward recovery requires cooldown hysteresis
        if target_weight < current_weight:
            elapsed = now - self._last_transition_time
            if elapsed >= self.cooldown_sec:
                logger.info(
                    "Recovering pipeline backpressure tier: %s -> %s after %.1fs cooldown",
                    self._current_tier.value,
                    target_tier.value,
                    elapsed,
                )
                self._current_tier = target_tier
                self._last_transition_time = now
                self._transitions_count += 1

        return self._current_tier

    def reset(self) -> None:
        """Reset backpressure state and metrics."""
        self._current_tier = DegradationTier.NORMAL
        self._last_transition_time = time.time()
        self._dropped_partials = 0
        self._transitions_count = 0
