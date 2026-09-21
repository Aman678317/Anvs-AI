"""Secret, Token and PII Sanitizer for Logging and Payloads (PR-18).

Prevents accidental exposure of API keys, JWT access tokens, passwords,
and encryption keys in structured logs and application traces.
"""

import re
from typing import Any

SENSITIVE_KEYS = {
    "password",
    "secret",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "livekit_api_secret",
    "livekit_token",
    "ws_ticket",
    "master_key",
    "encryption_key",
    "private_key",
}

BEARER_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9\-_.]+", re.IGNORECASE)
JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+")


class SecretSanitizer:
    """Sanitizes nested dictionaries, lists, and strings containing sensitive secrets."""

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Mask bearer tokens and raw JWTs within freeform strings."""
        masked = BEARER_PATTERN.sub(r"\1[MASKED_TOKEN]", text)
        return JWT_PATTERN.sub("[MASKED_JWT]", masked)

    @classmethod
    def sanitize(cls, data: Any) -> Any:
        """Recursively sanitize data structures."""
        if isinstance(data, dict):
            sanitized_dict: dict[str, Any] = {}
            for k, v in data.items():
                lower_key = str(k).lower()
                if any(sensitive in lower_key for sensitive in SENSITIVE_KEYS):
                    sanitized_dict[k] = "[REDACTED]"
                else:
                    sanitized_dict[k] = cls.sanitize(v)
            return sanitized_dict
        if isinstance(data, list):
            return [cls.sanitize(item) for item in data]
        if isinstance(data, tuple):
            return tuple(cls.sanitize(item) for item in data)
        if isinstance(data, str):
            return cls.sanitize_text(data)
        return data


def sanitize_payload(payload: Any) -> Any:
    """Convenience helper to sanitize arbitrary payload data."""
    return SecretSanitizer.sanitize(payload)
