"""OWASP Compliant Security Headers Middleware (PR-18).

Enforces Strict-Transport-Security, Content-Security-Policy, X-Frame-Options,
and X-Content-Type-Options on all outgoing HTTP responses.
"""

from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

SECURITY_HEADERS = {
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none';",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "microphone=('self'), camera=('self')",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects OWASP hardened security headers into all HTTP responses."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add hardened security headers to response."""
        response: Response = await call_next(request)
        for header, value in SECURITY_HEADERS.items():
            response.headers[header] = value
        return response
