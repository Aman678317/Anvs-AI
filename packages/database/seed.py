"""Database Seeding Utility for Local Development and Integration Testing."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Meeting, Organization, Participant, TranscriptSegment, User

DEFAULT_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
SECONDARY_TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")


async def seed_database(session: AsyncSession) -> dict[str, Any]:
    """Populate database with baseline multi-tenant seed fixtures."""
    # 1. Primary Tenant: Acme Corp
    tenant_stmt = select(Organization).where(Organization.id == DEFAULT_TENANT_ID)
    res = await session.execute(tenant_stmt)
    org = res.scalar_one_or_none()
    if not org:
        org = Organization(
            id=DEFAULT_TENANT_ID,
            name="Acme Corporation",
            slug="acme-corp",
        )
        session.add(org)

    # 2. Secondary Tenant: Globex Corp (for isolation verification)
    sec_tenant_stmt = select(Organization).where(Organization.id == SECONDARY_TENANT_ID)
    sec_res = await session.execute(sec_tenant_stmt)
    sec_org = sec_res.scalar_one_or_none()
    if not sec_org:
        sec_org = Organization(
            id=SECONDARY_TENANT_ID,
            name="Globex International",
            slug="globex-corp",
        )
        session.add(sec_org)

    # 3. Seed Host User
    user_id = uuid.UUID("10000000-0000-0000-0000-000000000001")
    user_stmt = select(User).where(User.id == user_id)
    user_res = await session.execute(user_stmt)
    host_user = user_res.scalar_one_or_none()
    if not host_user:
        host_user = User(
            id=user_id,
            tenant_id=DEFAULT_TENANT_ID,
            email="lead.host@acme.com",
            full_name="Sarah Connor",
            role="HOST",
            default_spoken_language="eng",
            default_listening_language="eng",
        )
        session.add(host_user)

    # 4. Seed Active Meeting
    meeting_id = uuid.UUID("20000000-0000-0000-0000-000000000001")
    meeting_stmt = select(Meeting).where(Meeting.id == meeting_id)
    meeting_res = await session.execute(meeting_stmt)
    meeting = meeting_res.scalar_one_or_none()
    if not meeting:
        meeting = Meeting(
            id=meeting_id,
            tenant_id=DEFAULT_TENANT_ID,
            created_by=user_id,
            title="Q3 Global Strategic Alignment",
            status="ACTIVE",
            state_version=1,
            host_spoken_language="eng",
            host_listening_language="jpn",
            scheduled_start=datetime.now(UTC),
            actual_start=datetime.now(UTC),
        )
        session.add(meeting)

    # 5. Seed Host Participant
    part_id = uuid.UUID("30000000-0000-0000-0000-000000000001")
    part_stmt = select(Participant).where(Participant.id == part_id)
    part_res = await session.execute(part_stmt)
    participant = part_res.scalar_one_or_none()
    if not participant:
        participant = Participant(
            id=part_id,
            tenant_id=DEFAULT_TENANT_ID,
            meeting_id=meeting_id,
            user_id=user_id,
            display_name="Sarah Connor (Host)",
            role="HOST",
            spoken_language="eng",
            listening_language="jpn",
            is_muted=False,
            is_video_enabled=True,
        )
        session.add(participant)

    # 6. Seed Lineaged Transcript Segment
    seg_id = uuid.UUID("40000000-0000-0000-0000-000000000001")
    seg_stmt = select(TranscriptSegment).where(TranscriptSegment.id == seg_id)
    seg_res = await session.execute(seg_stmt)
    segment = seg_res.scalar_one_or_none()
    if not segment:
        segment = TranscriptSegment(
            id=seg_id,
            tenant_id=DEFAULT_TENANT_ID,
            meeting_id=meeting_id,
            source_segment_id="src-seg-seed-001",
            speaker_id="spk-host-1",
            speaker_name="Sarah Connor",
            source_language="eng",
            target_language="spa",
            original_text="Welcome everyone to the quarterly platform briefing.",
            translated_text="Bienvenidos a todos a la sesión informativa trimestral.",
            start_ms=0,
            end_ms=3200,
            confidence=0.99,
            is_final=True,
        )
        session.add(segment)

    await session.commit()
    return {
        "tenant_id": str(DEFAULT_TENANT_ID),
        "secondary_tenant_id": str(SECONDARY_TENANT_ID),
        "host_user_id": str(user_id),
        "meeting_id": str(meeting_id),
        "participant_id": str(part_id),
        "segment_id": str(seg_id),
    }
