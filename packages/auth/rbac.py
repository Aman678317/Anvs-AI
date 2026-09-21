"""Role-Based Access Control (RBAC) and Permission Guards."""

from collections.abc import Callable
from enum import StrEnum

from fastapi import HTTPException, Request, status

from packages.contracts import ParticipantRole

from .models import AuthenticatedUser


class Permission(StrEnum):
    """Granular platform and meeting permissions."""

    MEETING_END = "meeting:end"
    MEETING_UPDATE = "meeting:update"
    PARTICIPANT_MUTE = "participant:mute"
    PARTICIPANT_REMOVE = "participant:remove"
    TRANSCRIPT_VIEW = "transcript:view"
    TRANSCRIPT_EXPORT = "transcript:export"
    AUDIO_PUBLISH = "audio:publish"
    ASSISTANT_QUERY = "assistant:query"


ROLE_HIERARCHY: dict[ParticipantRole, int] = {
    ParticipantRole.HOST: 40,
    ParticipantRole.MODERATOR: 30,
    ParticipantRole.PARTICIPANT: 20,
    ParticipantRole.GUEST: 10,
}

ROLE_PERMISSIONS: dict[ParticipantRole, set[Permission]] = {
    ParticipantRole.HOST: {
        Permission.MEETING_END,
        Permission.MEETING_UPDATE,
        Permission.PARTICIPANT_MUTE,
        Permission.PARTICIPANT_REMOVE,
        Permission.TRANSCRIPT_VIEW,
        Permission.TRANSCRIPT_EXPORT,
        Permission.AUDIO_PUBLISH,
        Permission.ASSISTANT_QUERY,
    },
    ParticipantRole.MODERATOR: {
        Permission.MEETING_UPDATE,
        Permission.PARTICIPANT_MUTE,
        Permission.PARTICIPANT_REMOVE,
        Permission.TRANSCRIPT_VIEW,
        Permission.TRANSCRIPT_EXPORT,
        Permission.AUDIO_PUBLISH,
        Permission.ASSISTANT_QUERY,
    },
    ParticipantRole.PARTICIPANT: {
        Permission.TRANSCRIPT_VIEW,
        Permission.AUDIO_PUBLISH,
        Permission.ASSISTANT_QUERY,
    },
    ParticipantRole.GUEST: {
        Permission.TRANSCRIPT_VIEW,
        Permission.ASSISTANT_QUERY,
    },
}


class PermissionDeniedError(Exception):
    """Raised when an authenticated user lacks the required permission."""

    pass


def has_permission(role: ParticipantRole, permission: Permission) -> bool:
    """Evaluate whether a given role holds a specific permission."""
    allowed = ROLE_PERMISSIONS.get(role, set())
    return permission in allowed


def check_role_satisfies_minimum(
    user_role: ParticipantRole,
    minimum_role: ParticipantRole,
) -> bool:
    """Check if the user's role meets or exceeds the minimum required role."""
    user_level = ROLE_HIERARCHY.get(user_role, 0)
    required_level = ROLE_HIERARCHY.get(minimum_role, 0)
    return user_level >= required_level


def require_role(
    minimum_role: ParticipantRole,
) -> Callable[..., AuthenticatedUser]:
    """FastAPI dependency factory enforcing a minimum role hierarchy."""

    def role_checker(request: Request | AuthenticatedUser) -> AuthenticatedUser:
        if isinstance(request, AuthenticatedUser):
            user = request
        else:
            user = getattr(request.state, "user", None)
            if not user or not isinstance(user, AuthenticatedUser):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        if not check_role_satisfies_minimum(user.role, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: requires minimum role '{minimum_role.value}', "
                    f"have '{user.role.value}'"
                ),
            )
        return user

    return role_checker


def require_permission(
    permission: Permission,
) -> Callable[..., AuthenticatedUser]:
    """FastAPI dependency factory enforcing a specific permission."""

    def permission_checker(request: Request | AuthenticatedUser) -> AuthenticatedUser:
        if isinstance(request, AuthenticatedUser):
            user = request
        else:
            user = getattr(request.state, "user", None)
            if not user or not isinstance(user, AuthenticatedUser):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Forbidden: missing required permission '{permission.value}'",
            )
        return user

    return permission_checker
