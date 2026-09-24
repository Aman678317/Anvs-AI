"""Token Bucket Rate Limiting Engine (PR-18).

Provides thread-safe token bucket rate limiting with automated refills,
quota tracking, and retry-after calculation per IP and per tenant.
"""

import math
import threading
import time

from packages.config import settings


class TokenBucketRateLimiter:
    """Thread-safe Token Bucket rate limiter for API and WebSocket protection."""

    def __init__(
        self,
        rate_per_minute: int | None = None,
        burst_capacity: int | None = None,
    ) -> None:
        self.rate_per_minute = (
            rate_per_minute
            if rate_per_minute is not None
            else settings.security_rate_limit_per_minute
        )
        self.capacity = float(
            burst_capacity if burst_capacity is not None else settings.security_rate_limit_burst
        )
        self.refill_rate = self.rate_per_minute / 60.0  # tokens per second
        self._buckets: dict[str, tuple[float, float]] = {}  # key -> (tokens, last_refill_time)
        self._lock = threading.Lock()

    def check(self, key: str, cost: int = 1) -> tuple[bool, int, float]:
        """Evaluate rate limit for a specific identifier.

        Returns:
            Tuple of:
            - is_allowed (bool): True if tokens were available and deducted.
            - remaining_tokens (int): Remaining tokens in the bucket.
            - retry_after_seconds (float): Seconds to wait before sufficient tokens refill.
        """
        now = time.time()
        with self._lock:
            tokens, last_refill = self._buckets.get(key, (self.capacity, now))

            # Calculate token refill since last check
            elapsed = max(0.0, now - last_refill)
            tokens = min(self.capacity, tokens + elapsed * self.refill_rate)

            if tokens >= cost:
                tokens -= cost
                self._buckets[key] = (tokens, now)
                return True, int(tokens), 0.0

            # Quota exhausted
            self._buckets[key] = (tokens, now)
            needed = cost - tokens
            retry_after = math.ceil(needed / self.refill_rate)
            return False, int(tokens), retry_after

    def reset(self, key: str | None = None) -> None:
        """Clear all buckets or a specific bucket key."""
        with self._lock:
            if key is not None:
                self._buckets.pop(key, None)
            else:
                self._buckets.clear()


default_rate_limiter = TokenBucketRateLimiter()
