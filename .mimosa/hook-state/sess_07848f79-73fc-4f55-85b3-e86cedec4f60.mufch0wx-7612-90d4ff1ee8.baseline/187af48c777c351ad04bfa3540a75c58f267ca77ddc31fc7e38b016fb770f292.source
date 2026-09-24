"""Unit tests for AES-256-GCM Cryptographic Engine & Key Derivation (PR-18)."""

import base64

import numpy as np
import pytest

from packages.security.crypto import (
    AuthenticationError,
    CryptoEngine,
    decrypt_text,
    decrypt_vector,
    encrypt_text,
    encrypt_vector,
)


@pytest.mark.unit
def test_aes_gcm_text_encryption_decryption_roundtrip() -> None:
    """Verifies AES-256-GCM authenticated encryption and decryption of string transcripts."""
    original_text = "Welcome to the Multilingual AI Meeting Platform. Real-time translation active."
    tenant_id = "00000000-0000-0000-0000-000000000001"

    encrypted = encrypt_text(original_text, tenant_id=tenant_id)
    assert encrypted != original_text
    assert isinstance(encrypted, str)

    # Decode base64 to assert envelope length (12-byte IV + ciphertext + 16-byte tag)
    raw = base64.b64decode(encrypted)
    assert len(raw) == 12 + len(original_text.encode("utf-8")) + 16

    decrypted = decrypt_text(encrypted, tenant_id=tenant_id)
    assert decrypted == original_text


@pytest.mark.unit
def test_aes_gcm_vector_encryption_decryption_roundtrip() -> None:
    """Verifies AES-256-GCM encryption and exact numeric recovery of float32 embeddings."""
    rng = np.random.default_rng(seed=42)
    original_vector = rng.standard_normal(1536).astype(np.float32)
    tenant_id = "00000000-0000-0000-0000-000000000002"

    encrypted_bytes = encrypt_vector(original_vector, tenant_id=tenant_id)
    assert isinstance(encrypted_bytes, bytes)
    # 12 bytes IV + 1536 * 4 bytes + 16 bytes tag
    assert len(encrypted_bytes) == 12 + (1536 * 4) + 16

    decrypted_vector = decrypt_vector(encrypted_bytes, tenant_id=tenant_id)
    assert decrypted_vector.shape == (1536,)
    assert decrypted_vector.dtype == np.float32
    assert np.allclose(original_vector, decrypted_vector, atol=1e-7)


@pytest.mark.unit
def test_tampered_ciphertext_fails_authentication() -> None:
    """Altering any byte in the ciphertext payload must raise an AuthenticationError."""
    engine = CryptoEngine()
    tenant_id = "00000000-0000-0000-0000-000000000003"
    encrypted = engine.encrypt_text("Sensitive executive transcript", tenant_id=tenant_id)

    raw = bytearray(base64.b64decode(encrypted))
    # Flip bits in the middle of ciphertext
    raw[15] ^= 0xFF
    tampered_b64 = base64.b64encode(raw).decode("ascii")

    with pytest.raises(AuthenticationError, match="Authenticated decryption failed"):
        engine.decrypt_text(tampered_b64, tenant_id=tenant_id)


@pytest.mark.unit
def test_tampered_tag_fails_authentication() -> None:
    """Tampering with the 128-bit authentication tag must trigger an AuthenticationError."""
    engine = CryptoEngine()
    tenant_id = "00000000-0000-0000-0000-000000000003"
    encrypted = engine.encrypt_text("Financial projection numbers", tenant_id=tenant_id)

    raw = bytearray(base64.b64decode(encrypted))
    # Flip bits in the final byte (within the 16-byte authentication tag)
    raw[-1] ^= 0xFF
    tampered_b64 = base64.b64encode(raw).decode("ascii")

    with pytest.raises(AuthenticationError, match="Authenticated decryption failed"):
        engine.decrypt_text(tampered_b64, tenant_id=tenant_id)


@pytest.mark.unit
def test_tenant_key_isolation() -> None:
    """Different tenants have cryptographically isolated DEKs and cannot cross-decrypt."""
    engine = CryptoEngine()
    tenant_a = "11111111-1111-1111-1111-111111111111"
    tenant_b = "22222222-2222-2222-2222-222222222222"

    key_a = engine.derive_tenant_key(tenant_a)
    key_b = engine.derive_tenant_key(tenant_b)
    assert key_a != key_b
    assert len(key_a) == 32
    assert len(key_b) == 32

    # Encrypt under tenant_a
    encrypted_a = engine.encrypt_text("Acme Corp Proprietary Strategy", tenant_id=tenant_a)

    # Attempt to decrypt under tenant_b must fail
    with pytest.raises(AuthenticationError):
        engine.decrypt_text(encrypted_a, tenant_id=tenant_b)


@pytest.mark.unit
def test_hkdf_key_derivation_deterministic() -> None:
    """Deriving the key for the same tenant must always produce identical key material."""
    engine = CryptoEngine()
    tenant_id = "33333333-3333-3333-3333-333333333333"

    key1 = engine.derive_tenant_key(tenant_id)
    key2 = engine.derive_tenant_key(tenant_id)
    assert key1 == key2


@pytest.mark.unit
def test_unicode_and_multilingual_transcript_encryption() -> None:
    """Verifies that non-ASCII and multibyte UTF-8 scripts encrypt and decrypt accurately."""
    multilingual_text = (
        "Bonjour le monde! 🌍 "
        "こんにちは世界 🇯🇵 "
        "你好世界 🇨🇳 "
        "مرحبا بالعالم 🇸🇦 "
        "नमस्ते दुनिया 🇮🇳"
    )
    tenant_id = "44444444-4444-4444-4444-444444444444"

    encrypted = encrypt_text(multilingual_text, tenant_id=tenant_id)
    decrypted = decrypt_text(encrypted, tenant_id=tenant_id)
    assert decrypted == multilingual_text
