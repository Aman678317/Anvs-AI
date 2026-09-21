"""Global pytest configuration and automatic test isolation fixtures."""

import pytest

from packages.security.rate_limit import default_rate_limiter


@pytest.fixture(autouse=True)
def reset_rate_limiter_before_test() -> None:
    """Automatically resets the in-memory token bucket rate limiter before each test.

    Prevents rate limit quota exhaustion (HTTP 429) across large test suite runs.
    """
    default_rate_limiter.reset()
