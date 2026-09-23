"""Meeting Room Lifecycle & LiveKit SFU Integration Router."""

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.auth import AuthenticatedUser, create_session_ticket
from packages.contracts import (
    CreateMeetingRequest,
    CreateMeetingResponse,
    GetMeetingResponse,
    JoinMeetingRequest,
    JoinMeetingResponse,
    MeetingStatus,
    ParticipantRole,
)
from packages.database.models import Meeting, Participant
from services.api.middleware.tenant import (
    get_authenticated_tenant_session,
    get_current_user,
)
from services.api.services import livekit_service

router = APIRouter(prefix="/api/v1/rooms", tags=["Rooms & LiveKit"])


@router.post(
    "",
    response_model=CreateMeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new meeting room",
)
@router.post(
    "/create",
    response_model=CreateMeetingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new meeting room (alias)",
)
async def create_room(
    payload: CreateMeetingRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authenticated_tenant_session),
) -> CreateMeetingResponse:
    """Provisions a meeting in the database and creates an associated LiveKit SFU room."""
    meeting_id = uuid.uuid4()
    tenant_uuid = uuid.UUID(current_user.tenant_id)
    try:
        creator_uuid: uuid.UUID | None = uuid.UUID(current_user.user_id)
    except (ValueError, TypeError):
        creator_uuid = None

    passcode_hash = None
    if payload.passcode:
        passcode_hash = hashlib.sha256(payload.passcode.encode("utf-8")).hexdigest()

    now = datetime.now(UTC)
    meeting = Meeting(
        id=meeting_id,
        tenant_id=tenant_uuid,
        created_by=creator_uuid,
        title=payload.title,
        status="SCHEDULED",
        state_version=1,
        host_spoken_language=payload.host_spoken_language,
        host_listening_language=payload.host_listening_language,
        passcode_hash=passcode_hash,
        scheduled_start=payload.scheduled_start,
        created_at=now,
        updated_at=now,
    )
    add_res = session.add(meeting)
    if asyncio.iscoroutine(add_res):
        await add_res

    # Provision room in LiveKit SFU
    await livekit_service.create_room(room_name=f"room_{meeting_id}")

    return CreateMeetingResponse(
        meeting_id=str(meeting.id),
        tenant_id=str(meeting.tenant_id),
        title=meeting.title,
        status=MeetingStatus.SCHEDULED,
        state_version=meeting.state_version,
        created_at=meeting.created_at,
    )


@router.get(
    "/{meeting_id}",
    response_model=GetMeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve meeting status and active participant count",
)
async def get_room(
    meeting_id: str,
    _current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authenticated_tenant_session),
) -> GetMeetingResponse:
    """Fetch meeting room status, versioning, and participant counts."""
    try:
        target_uuid = uuid.UUID(meeting_id)
    except ValueError:
        target_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, meeting_id)

    stmt = select(Meeting).where(Meeting.id == target_uuid)
    res = await session.execute(stmt)
    meeting = res.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    # Count active participants
    count_stmt = select(func.count(Participant.id)).where(
        Participant.meeting_id == target_uuid,
        Participant.left_at.is_(None),
    )
    count_res = await session.execute(count_stmt)
    active_count = count_res.scalar() or 0

    return GetMeetingResponse(
        meeting_id=str(meeting.id),
        tenant_id=str(meeting.tenant_id),
        title=meeting.title,
        status=MeetingStatus(meeting.status),
        state_version=meeting.state_version,
        created_at=meeting.created_at,
        active_participants_count=int(active_count),
    )


@router.post(
    "/{meeting_id}/join",
    response_model=JoinMeetingResponse,
    status_code=status.HTTP_200_OK,
    summary="Join meeting room and acquire dual tokens (LiveKit SFU + WebSocket)",
)
async def join_room(
    meeting_id: str,
    payload: JoinMeetingRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authenticated_tenant_session),
) -> JoinMeetingResponse:
    """Validates meeting eligibility and issues LiveKit WebRTC token and WebSocket ticket."""
    try:
        target_uuid = uuid.UUID(meeting_id)
    except ValueError:
        target_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, meeting_id)

    stmt = select(Meeting).where(Meeting.id == target_uuid)
    res = await session.execute(stmt)
    meeting = res.scalar_one_or_none()

    if not meeting:
        now = datetime.now(UTC)
        try:
            tenant_uuid = uuid.UUID(current_user.tenant_id)
        except (ValueError, TypeError):
            tenant_uuid = uuid.uuid4()

        meeting = Meeting(
            id=target_uuid,
            tenant_id=tenant_uuid,
            created_by=None,
            title=f"AI Meeting Room ({meeting_id})",
            status="ACTIVE",
            state_version=1,
            host_spoken_language=payload.spoken_language or "eng",
            host_listening_language=payload.listening_language or "eng",
            created_at=now,
            updated_at=now,
        )
        session.add(meeting)
        await livekit_service.create_room(room_name=f"room_{meeting.id}")

    if meeting.status in ("ENDED", "ARCHIVED"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Meeting has already ended"
        )

    # Passcode verification if configured
    if meeting.passcode_hash:
        if not payload.passcode:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Meeting passcode required"
            )
        candidate_hash = hashlib.sha256(payload.passcode.encode("utf-8")).hexdigest()
        if candidate_hash != meeting.passcode_hash:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Invalid meeting passcode"
            )

    # Transition from SCHEDULED to ACTIVE on first participant join
    if meeting.status == "SCHEDULED":
        meeting.status = "ACTIVE"
        meeting.actual_start = datetime.now(UTC)
        meeting.state_version += 1

    try:
        user_uuid: uuid.UUID | None = uuid.UUID(current_user.user_id)
    except (ValueError, TypeError):
        user_uuid = None

    participant_id = uuid.uuid4()
    participant = Participant(
        id=participant_id,
        tenant_id=meeting.tenant_id,
        meeting_id=meeting.id,
        user_id=user_uuid,
        display_name=payload.display_name,
        role=current_user.role.value,
        spoken_language=payload.spoken_language,
        listening_language=payload.listening_language,
        is_muted=False,
        is_video_enabled=True,
    )
    add_res = session.add(participant)
    if asyncio.iscoroutine(add_res):
        await add_res

    # 1. Generate LiveKit WebRTC access token
    livekit_token = livekit_service.generate_token(
        room_name=f"room_{meeting.id}",
        identity=str(participant.id),
        name=payload.display_name,
        role=current_user.role,
        metadata={
            "tenant_id": str(meeting.tenant_id),
            "spoken_language": payload.spoken_language,
            "listening_language": payload.listening_language,
            "role": current_user.role.value,
        },
    )

    # 2. Generate WebSocket session ticket
    ws_ticket = create_session_ticket(
        user=current_user,
        meeting_id=str(meeting.id),
    )

    return JoinMeetingResponse(
        meeting_id=str(meeting.id),
        participant_id=str(participant.id),
        display_name=participant.display_name,
        role=current_user.role,
        livekit_token=livekit_token,
        ws_ticket=ws_ticket,
        state_version=meeting.state_version,
    )


@router.post(
    "/{meeting_id}/end",
    status_code=status.HTTP_200_OK,
    summary="End meeting and tear down LiveKit SFU room",
)
async def end_room(
    meeting_id: str,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_authenticated_tenant_session),
) -> dict[str, Any]:
    """Terminates meeting and cleans up LiveKit WebRTC resources (Host only)."""
    if current_user.role != ParticipantRole.HOST:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the meeting host can end the meeting.",
        )

    try:
        target_uuid = uuid.UUID(meeting_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid meeting ID",
        ) from e

    stmt = select(Meeting).where(Meeting.id == target_uuid)
    res = await session.execute(stmt)
    meeting = res.scalar_one_or_none()

    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting not found")

    meeting.status = "ENDED"
    meeting.actual_end = datetime.now(UTC)
    meeting.state_version += 1

    # Teardown LiveKit room
    await livekit_service.delete_room(room_name=f"room_{meeting.id}")

    return {
        "status": "ENDED",
        "meeting_id": str(meeting.id),
        "state_version": meeting.state_version,
    }


@router.get(
    "/{meeting_id}/sfu-participants",
    status_code=status.HTTP_200_OK,
    summary="List active LiveKit SFU participants",
)
async def list_sfu_participants(
    meeting_id: str,
    _current_user: AuthenticatedUser = Depends(get_current_user),
    _session: AsyncSession = Depends(get_authenticated_tenant_session),
) -> dict[str, Any]:
    """Retrieves active WebRTC peer participants directly from LiveKit SFU."""
    participants = await livekit_service.list_participants(room_name=f"room_{meeting_id}")
    return {
        "meeting_id": meeting_id,
        "participants": participants,
        "count": len(participants),
    }


@router.post(
    "/webhook",
    status_code=status.HTTP_200_OK,
    summary="Handle LiveKit SFU Webhook callbacks",
)
async def livekit_webhook(request: Request) -> dict[str, Any]:
    """Ingests LiveKit WebRTC presence and media track state events."""
    raw_body = await request.body()
    auth_header = request.headers.get("Authorization", "")

    try:
        event = livekit_service.verify_webhook(raw_body, auth_header)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook verification failed: {e}",
        ) from e

    dispatched = await livekit_service.dispatch_webhook_event(event)

    return {
        "status": "processed",
        "event": event.get("event"),
        "room": event.get("room", {}).get("name"),
        "details": dispatched,
    }
