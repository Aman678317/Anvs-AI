"""Password Hashing and Constant-Time Verification Utilities (PR-02)."""

import bcrypt


def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt with automatic salting."""
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str | None) -> bool:
    """Verify a plaintext password against a bcrypt hash in constant time."""
    if not hashed_password or not plain_password:
        return False
    try:
        plain_bytes = plain_password.encode("utf-8")[:72]
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(plain_bytes, hash_bytes)
    except (ValueError, TypeError):
        return False

