"""Rate Limiting Middleware for FastAPI / Starlette (PR-18).

Applies dual-tier rate limiting (Per-IP and Per-Tenant) and emits standard
X-RateLimit-* and Retry-After HTTP headers.
"""

import time
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from packages.config import settings
from packages.security.rate_limit import default_rate_limiter

EXEMPT_PATHS = {"/healthz", "/metrics", "/docs", "/redoc", "/openapi.json"}


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Intercepts HTTP requests to enforce rate limits with standard HTTP 429 responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process inbound request through rate limiter."""
        if not settings.security_rate_limit_enabled:
            return await call_next(request)

        # Skip probes and documentation paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Determine rate limit bucket key (prefer tenant_id if resolved, otherwise client IP)
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            key = f"tenant:{tenant_id}"
        else:
            client_ip = request.client.host if request.client else "127.0.0.1"
            key = f"ip:{client_ip}"

        allowed, remaining, retry_after = default_rate_limiter.check(key)

        if not allowed:
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(default_rate_limiter.rate_per_minute),
                "X-RateLimit-Remaining": "0",
            }
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests: Rate limit quota exceeded"},
                headers=headers,
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(default_rate_limiter.rate_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + 60))
        return response
