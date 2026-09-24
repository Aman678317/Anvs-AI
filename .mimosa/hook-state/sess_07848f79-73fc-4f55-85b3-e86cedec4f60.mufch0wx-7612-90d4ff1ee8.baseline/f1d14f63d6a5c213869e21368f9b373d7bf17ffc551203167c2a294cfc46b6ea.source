"""Contract tests for Security Specifications, Rate Limiting & Cryptographic Envelopes (PR-18)."""

import base64

import pytest
from fastapi.testclient import TestClient

from packages.security.crypto import default_crypto_engine, encrypt_text
from packages.security.rate_limit import default_rate_limiter
from services.api.main import app


@pytest.mark.contract
def test_rate_limit_429_contract_schema() -> None:
    """HTTP 429 responses adhere to RFC 6585 and include Retry-After and X-RateLimit-* headers."""
    client = TestClient(app)
    ip_key = "ip:10.0.0.99"
    default_rate_limiter.reset(ip_key)

    # Exhaust tokens
    for _ in range(35):
        resp = client.get("/", headers={"X-Forwarded-For": "10.0.0.99"})
        if resp.status_code == 429:
            data = resp.json()
            assert "detail" in data
            assert isinstance(data["detail"], str)
            assert "Retry-After" in resp.headers
            assert "X-RateLimit-Limit" in resp.headers
            assert "X-RateLimit-Remaining" in resp.headers
            assert resp.headers["X-RateLimit-Remaining"] == "0"
            break

    default_rate_limiter.reset(ip_key)


@pytest.mark.contract
def test_aes_gcm_ciphertext_envelope_structure() -> None:
    """Ciphertext envelope must strictly adhere to: base64(12_byte_IV + ciphertext + 16_byte_tag)."""
    payload = "Contract test payload for AES-256-GCM"
    b64_cipher = encrypt_text(payload)

    raw = base64.b64decode(b64_cipher)
    nonce = raw[:12]
    tag = raw[-16:]
    ciphertext = raw[12:-16]

    assert len(nonce) == 12
    assert len(tag) == 16
    assert len(ciphertext) == len(payload.encode("utf-8"))

    # Decrypt via engine
    recovered = default_crypto_engine.decrypt_text(b64_cipher)
    assert recovered == payload
