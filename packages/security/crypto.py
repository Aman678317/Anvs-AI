"""AES-256-GCM Authenticated Cryptographic Engine & Key Derivation (PR-18).

Provides authenticated encryption with associated data (AEAD) using AES-256-GCM,
per-tenant Data Encryption Key (DEK) derivation via HKDF-SHA256, and transparent
column-level encryption for SQLAlchemy models.
"""

import base64
import os
from typing import Any

import numpy as np
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from sqlalchemy.types import String, TypeDecorator

from packages.config import settings


class CryptographicError(Exception):
    """Base exception for all cryptographic operations."""


class AuthenticationError(CryptographicError):
    """Raised when ciphertext payload is tampered with or tag verification fails."""


class CryptoEngine:
    """Enterprise AES-256-GCM cryptographic engine with HKDF tenant key derivation."""

    def __init__(self, master_key: str | bytes | None = None) -> None:
        key_input = master_key if master_key is not None else settings.security_master_encryption_key
        if isinstance(key_input, str):
            if len(key_input) == 64:
                self.master_key = bytes.fromhex(key_input)
            else:
                self.master_key = key_input.encode("utf-8").ljust(32, b"\0")[:32]
        else:
            self.master_key = key_input[:32].ljust(32, b"\0")

    def derive_tenant_key(self, tenant_id: str) -> bytes:
        """Derive a cryptographically isolated 256-bit DEK for a specific tenant."""
        hkdf = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=tenant_id.encode("utf-8"),
            info=b"tenant-aes-256-gcm-dek",
        )
        return hkdf.derive(self.master_key)

    def _resolve_key(self, tenant_id: str | None = None, key: bytes | None = None) -> bytes:
        if key is not None:
            return key
        if tenant_id is not None:
            return self.derive_tenant_key(tenant_id)
        return self.master_key

    def encrypt_text(
        self,
        plaintext: str,
        tenant_id: str | None = None,
        key: bytes | None = None,
    ) -> str:
        """Encrypt plaintext string using AES-256-GCM and return base64 envelope."""
        encryption_key = self._resolve_key(tenant_id=tenant_id, key=key)
        nonce = os.urandom(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), associated_data=None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt_text(
        self,
        encrypted_b64: str,
        tenant_id: str | None = None,
        key: bytes | None = None,
    ) -> str:
        """Decrypt base64 AES-256-GCM envelope and verify 128-bit authentication tag."""
        try:
            raw = base64.b64decode(encrypted_b64)
        except Exception as err:
            raise AuthenticationError("Invalid base64 payload") from err

        if len(raw) < 28:
            raise AuthenticationError("Malformed ciphertext payload: minimum 28 bytes required")

        nonce = raw[:12]
        ciphertext = raw[12:]
        encryption_key = self._resolve_key(tenant_id=tenant_id, key=key)
        aesgcm = AESGCM(encryption_key)

        try:
            decrypted = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            return decrypted.decode("utf-8")
        except InvalidTag as err:
            raise AuthenticationError(
                "Authenticated decryption failed: invalid tag or tampered ciphertext"
            ) from err

    def encrypt_vector(
        self,
        vector: np.ndarray,
        tenant_id: str | None = None,
        key: bytes | None = None,
    ) -> bytes:
        """Encrypt float array embedding using AES-256-GCM and return raw bytes."""
        encryption_key = self._resolve_key(tenant_id=tenant_id, key=key)
        vec_bytes = np.asarray(vector, dtype=np.float32).tobytes()
        nonce = os.urandom(12)
        aesgcm = AESGCM(encryption_key)
        ciphertext = aesgcm.encrypt(nonce, vec_bytes, associated_data=None)
        return nonce + ciphertext

    def decrypt_vector(
        self,
        encrypted_bytes: bytes,
        tenant_id: str | None = None,
        key: bytes | None = None,
        dtype: Any = np.float32,
    ) -> np.ndarray:
        """Decrypt AES-256-GCM bytes back into NumPy vector embedding."""
        if len(encrypted_bytes) < 28:
            raise AuthenticationError("Malformed vector ciphertext: minimum 28 bytes required")

        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]
        encryption_key = self._resolve_key(tenant_id=tenant_id, key=key)
        aesgcm = AESGCM(encryption_key)

        try:
            raw_vec = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
            return np.frombuffer(raw_vec, dtype=dtype)
        except InvalidTag as err:
            raise AuthenticationError(
                "Authenticated vector decryption failed: invalid tag or tampered ciphertext"
            ) from err


default_crypto_engine = CryptoEngine()


def encrypt_text(plaintext: str, tenant_id: str | None = None) -> str:
    """Convenience helper to encrypt text using default crypto engine."""
    return default_crypto_engine.encrypt_text(plaintext, tenant_id=tenant_id)


def decrypt_text(encrypted_b64: str, tenant_id: str | None = None) -> str:
    """Convenience helper to decrypt text using default crypto engine."""
    return default_crypto_engine.decrypt_text(encrypted_b64, tenant_id=tenant_id)


def encrypt_vector(vector: np.ndarray, tenant_id: str | None = None) -> bytes:
    """Convenience helper to encrypt vector using default crypto engine."""
    return default_crypto_engine.encrypt_vector(vector, tenant_id=tenant_id)


def decrypt_vector(encrypted_bytes: bytes, tenant_id: str | None = None) -> np.ndarray:
    """Convenience helper to decrypt vector using default crypto engine."""
    return default_crypto_engine.decrypt_vector(encrypted_bytes, tenant_id=tenant_id)


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator that encrypts text with AES-256-GCM at rest."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value: Any, _dialect: Any) -> Any:
        if value is None:
            return None
        return default_crypto_engine.encrypt_text(str(value))

    def process_result_value(self, value: Any, _dialect: Any) -> Any:
        if value is None:
            return None
        return default_crypto_engine.decrypt_text(str(value))
