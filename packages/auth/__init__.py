"""Authentication and Authorization package (Supabase JWT & RBAC)."""

from .models import AuthenticatedUser, JWTPayload, SessionTicket
from .passwords import hash_password, verify_password
from .rbac import (
    ROLE_HIERARCHY,
    ROLE_PERMISSIONS,
    Permission,
    PermissionDeniedError,
    check_role_satisfies_minimum,
    has_permission,
    require_permission,
    require_role,
)
from .tokens import (
    AuthenticationError,
    InvalidTokenError,
    TokenExpiredError,
    create_access_token,
    create_session_ticket,
    verify_session_ticket,
    verify_token,
)

__all__ = [
    "ROLE_HIERARCHY",
    "ROLE_PERMISSIONS",
    "AuthenticatedUser",
    "AuthenticationError",
    "InvalidTokenError",
    "JWTPayload",
    "Permission",
    "PermissionDeniedError",
    "SessionTicket",
    "TokenExpiredError",
    "check_role_satisfies_minimum",
    "create_access_token",
    "create_session_ticket",
    "has_permission",
    "hash_password",
    "require_permission",
    "require_role",
    "verify_password",
    "verify_session_ticket",
    "verify_token",
]
