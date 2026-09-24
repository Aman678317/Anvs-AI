"""Unit tests for Security Middleware, Rate Limiting & Secret Sanitizer (PR-18)."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from packages.security.compliance import ComplianceManager
from packages.security.rate_limit import TokenBucketRateLimiter, default_rate_limiter
from packages.security.sanitizer import SecretSanitizer, sanitize_payload
from services.api.main import app


@pytest.mark.unit
def test_token_bucket_allows_and_deducts_tokens() -> None:
    """Rate limiter allows requests within capacity and tracks remaining count."""
    limiter = TokenBucketRateLimiter(rate_per_minute=60, burst_capacity=5)
    key = "test-client-ip"

    for i in range(5):
        allowed, remaining, retry_after = limiter.check(key, cost=1)
        assert allowed is True
        assert remaining == 4 - i
        assert retry_after == 0.0

    # 6th request must be rejected
    allowed, remaining, retry_after = limiter.check(key, cost=1)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0.0


@pytest.mark.unit
def test_token_bucket_refill() -> None:
    """Rate limiter replenishes tokens after time passes."""
    limiter = TokenBucketRateLimiter(rate_per_minute=600, burst_capacity=10)
    key = "refill-client"

    # Consume all 10 tokens
    for _ in range(10):
        limiter.check(key)

    allowed, _, _ = limiter.check(key)
    assert allowed is False

    # Reset or clear bucket
    limiter.reset(key)
    allowed, remaining, _ = limiter.check(key)
    assert allowed is True
    assert remaining == 9


@pytest.mark.unit
def test_security_headers_middleware_injected() -> None:
    """All responses must contain OWASP recommended security headers."""
    client = TestClient(app)
    response = client.get("/healthz")

    assert response.status_code == 200
    headers = response.headers
    assert headers["X-Content-Type-Options"] == "nosniff"
    assert headers["X-Frame-Options"] == "DENY"
    assert "Strict-Transport-Security" in headers
    assert "Content-Security-Policy" in headers
    assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"


@pytest.mark.unit
def test_rate_limit_middleware_exceeds_quota() -> None:
    """Repeated rapid requests from same client trigger HTTP 429 Too Many Requests."""
    client = TestClient(app)
    # Target a unique client ip for testing
    unique_ip = "192.168.100.99"
    key = f"ip:{unique_ip}"
    default_rate_limiter.reset(key)

    # Exhaust quota using burst capacity + 5
    exhausted = False
    for _ in range(50):
        resp = client.get("/", headers={"X-Forwarded-For": unique_ip})
        if resp.status_code == 429:
            exhausted = True
            assert "Retry-After" in resp.headers
            assert "X-RateLimit-Remaining" in resp.headers
            assert resp.json()["detail"] == "Too Many Requests: Rate limit quota exceeded"
            break

    # Clean up state
    default_rate_limiter.reset(key)
    assert exhausted is True


@pytest.mark.unit
def test_secret_sanitizer_masks_sensitive_data() -> None:
    """SecretSanitizer masks tokens, keys, and passwords across structures and strings."""
    payload = {
        "username": "alice",
        "password": "SuperSecretPassword123!",
        "api_key": "sk-live-999888777",
        "auth_header": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz.abc",
        "nested": {
            "token": "secret_ticket_456",
            "safe_metric": 42.5,
        },
    }

    sanitized = sanitize_payload(payload)
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["api_key"] == "[REDACTED]"
    assert sanitized["nested"]["token"] == "[REDACTED]"
    assert sanitized["nested"]["safe_metric"] == 42.5
    assert "[MASKED_TOKEN]" in sanitized["auth_header"]
    assert "SuperSecretPassword123!" not in str(sanitized)

    # Verify class-level string masking helper directly
    text_masked = SecretSanitizer.sanitize_text("Bearer auth_token_secret_123")
    assert text_masked == "Bearer [MASKED_TOKEN]"

    nvapi_masked = SecretSanitizer.sanitize_text("Using key nvapi-123456789abcdef for NIM")
    assert "nvapi-123456789abcdef" not in nvapi_masked
    assert "[MASKED_API_KEY]" in nvapi_masked

    pg_masked = SecretSanitizer.sanitize_text(
        "postgresql+asyncpg://postgres.user:SecretPassword123@aws-0-pooler.supabase.com:6543/postgres"
    )
    assert "SecretPassword123" not in pg_masked
    assert "[REDACTED_PASSWORD]" in pg_masked


@pytest.mark.asyncio
@pytest.mark.unit
async def test_compliance_manager_shred_meeting_data() -> None:
    """ComplianceManager executes deletion within tenant boundary and reports counts."""
    mock_session = AsyncMock()
    mock_emb_res = MagicMock()
    mock_emb_res.rowcount = 15
    mock_seg_res = MagicMock()
    mock_seg_res.rowcount = 15
    mock_session.execute.side_effect = [mock_emb_res, mock_seg_res]

    tenant_id = str(uuid.uuid4())
    meeting_id = str(uuid.uuid4())

    result = await ComplianceManager.shred_meeting_data(
        session=mock_session,
        tenant_id=tenant_id,
        meeting_id=meeting_id,
    )

    assert result["shredded_embeddings"] == 15
    assert result["shredded_segments"] == 15
    assert mock_session.execute.call_count == 2
    mock_session.flush.assert_awaited_once()
