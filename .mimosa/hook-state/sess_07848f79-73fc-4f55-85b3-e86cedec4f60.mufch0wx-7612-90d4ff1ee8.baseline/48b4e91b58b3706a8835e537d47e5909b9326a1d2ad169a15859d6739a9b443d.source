"""Initial schema, pgvector extension, and PostgreSQL 16 RLS policies.

Revision ID: 0001
Revises:
Create Date: 2026-09-20 18:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TENANT_TABLES = [
    "users",
    "meetings",
    "participants",
    "transcript_segments",
    "transcript_embeddings",
]


def upgrade() -> None:
    # 1. Extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector";')

    # 2. Table: organizations
    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_organizations_slug", "organizations", ["slug"])

    # 3. Table: users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=100), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), server_default="PARTICIPANT", nullable=False),
        sa.Column(
            "default_spoken_language", sa.String(length=3), server_default="eng", nullable=False
        ),
        sa.Column(
            "default_listening_language", sa.String(length=3), server_default="eng", nullable=False
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_users_tenant_id", "users", ["tenant_id"])
    op.create_index("idx_users_email", "users", ["email"])

    # 4. Table: meetings
    op.create_table(
        "meetings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="SCHEDULED", nullable=False),
        sa.Column("state_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "host_spoken_language", sa.String(length=3), server_default="eng", nullable=False
        ),
        sa.Column(
            "host_listening_language", sa.String(length=3), server_default="eng", nullable=False
        ),
        sa.Column("passcode_hash", sa.String(length=255), nullable=True),
        sa.Column("scheduled_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_meetings_tenant_id", "meetings", ["tenant_id"])

    # 5. Table: participants
    op.create_table(
        "participants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("display_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=50), server_default="PARTICIPANT", nullable=False),
        sa.Column("spoken_language", sa.String(length=3), server_default="eng", nullable=False),
        sa.Column("listening_language", sa.String(length=3), server_default="eng", nullable=False),
        sa.Column("is_muted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_video_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_participants_meeting_id", "participants", ["meeting_id"])
    op.create_index("idx_participants_tenant_id", "participants", ["tenant_id"])

    # 6. Table: transcript_segments
    op.create_table(
        "transcript_segments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_segment_id", sa.String(length=100), nullable=False),
        sa.Column("speaker_id", sa.String(length=100), nullable=False),
        sa.Column("speaker_name", sa.String(length=100), nullable=False),
        sa.Column("source_language", sa.String(length=3), nullable=False),
        sa.Column("target_language", sa.String(length=3), nullable=False),
        sa.Column("original_text", sa.Text(), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("confidence", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("is_final", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_segments_meeting_id", "transcript_segments", ["meeting_id"])
    op.create_index("idx_segments_source_segment_id", "transcript_segments", ["source_segment_id"])
    op.create_index("idx_segments_tenant_id", "transcript_segments", ["tenant_id"])

    # 7. Table: transcript_embeddings (pgvector)
    op.execute(
        """
        CREATE TABLE transcript_embeddings (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            meeting_id UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
            segment_id UUID NOT NULL UNIQUE REFERENCES transcript_segments(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            embedding vector(1536) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE INDEX idx_transcript_embeddings_hnsw
        ON transcript_embeddings USING hnsw (embedding vector_cosine_ops);
        """
    )

    # 8. Row Level Security (RLS) - Invariant #1: Strict Multi-Tenancy Isolation
    for table in TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            """
        )


def downgrade() -> None:
    for table in reversed(TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.drop_table("transcript_embeddings")
    op.drop_table("transcript_segments")
    op.drop_table("participants")
    op.drop_table("meetings")
    op.drop_table("users")
    op.drop_table("organizations")
