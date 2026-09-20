"""Unit tests for Role-Based Access Control (RBAC) and Permission Guards."""

import uuid

import pytest
from fastapi import HTTPException

from packages.auth import (
    AuthenticatedUser,
    Permission,
    check_role_satisfies_minimum,
    has_permission,
    require_permission,
    require_role,
)
from packages.contracts import ParticipantRole


@pytest.fixture
def host_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="host@company.com",
        role=ParticipantRole.HOST,
    )


@pytest.fixture
def participant_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="participant@company.com",
        role=ParticipantRole.PARTICIPANT,
    )


@pytest.fixture
def observer_user() -> AuthenticatedUser:
    return AuthenticatedUser(
        user_id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email="observer@company.com",
        role=ParticipantRole.OBSERVER,
    )


@pytest.mark.unit
def test_role_hierarchy_checks() -> None:
    # HOST satisfies all minimum levels
    assert check_role_satisfies_minimum(ParticipantRole.HOST, ParticipantRole.HOST) is True
    assert check_role_satisfies_minimum(ParticipantRole.HOST, ParticipantRole.CO_HOST) is True
    assert check_role_satisfies_minimum(ParticipantRole.HOST, ParticipantRole.PARTICIPANT) is True
    assert check_role_satisfies_minimum(ParticipantRole.HOST, ParticipantRole.OBSERVER) is True

    # PARTICIPANT satisfies PARTICIPANT and OBSERVER, but NOT HOST
    assert (
        check_role_satisfies_minimum(ParticipantRole.PARTICIPANT, ParticipantRole.PARTICIPANT)
        is True
    )
    assert (
        check_role_satisfies_minimum(ParticipantRole.PARTICIPANT, ParticipantRole.OBSERVER) is True
    )
    assert check_role_satisfies_minimum(ParticipantRole.PARTICIPANT, ParticipantRole.HOST) is False
    assert (
        check_role_satisfies_minimum(ParticipantRole.PARTICIPANT, ParticipantRole.CO_HOST) is False
    )


@pytest.mark.unit
def test_permission_matrix() -> None:
    # Only HOST has MEETING_END
    assert has_permission(ParticipantRole.HOST, Permission.MEETING_END) is True
    assert has_permission(ParticipantRole.CO_HOST, Permission.MEETING_END) is False
    assert has_permission(ParticipantRole.PARTICIPANT, Permission.MEETING_END) is False
    assert has_permission(ParticipantRole.OBSERVER, Permission.MEETING_END) is False

    # PARTICIPANT can publish audio and query assistant
    assert has_permission(ParticipantRole.PARTICIPANT, Permission.AUDIO_PUBLISH) is True
    assert has_permission(ParticipantRole.PARTICIPANT, Permission.ASSISTANT_QUERY) is True
    assert has_permission(ParticipantRole.PARTICIPANT, Permission.PARTICIPANT_MUTE) is False

    # OBSERVER can only view transcripts and query assistant
    assert has_permission(ParticipantRole.OBSERVER, Permission.TRANSCRIPT_VIEW) is True
    assert has_permission(ParticipantRole.OBSERVER, Permission.AUDIO_PUBLISH) is False


@pytest.mark.unit
def test_require_role_guard(
    host_user: AuthenticatedUser, participant_user: AuthenticatedUser
) -> None:
    guard = require_role(ParticipantRole.HOST)

    # Allowed for host
    result = guard(host_user)
    assert result is host_user

    # Forbidden for participant (raises 403)
    with pytest.raises(HTTPException) as exc_info:
        guard(participant_user)
    assert exc_info.value.status_code == 403
    assert "Forbidden" in exc_info.value.detail


@pytest.mark.unit
def test_require_permission_guard(
    host_user: AuthenticatedUser, participant_user: AuthenticatedUser
) -> None:
    guard = require_permission(Permission.MEETING_END)

    # Allowed for host
    result = guard(host_user)
    assert result is host_user

    # Forbidden for participant (raises 403)
    with pytest.raises(HTTPException) as exc_info:
        guard(participant_user)
    assert exc_info.value.status_code == 403
    assert "Forbidden: missing required permission" in exc_info.value.detail
