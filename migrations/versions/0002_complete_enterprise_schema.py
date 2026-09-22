"""Complete enterprise schema: 8 additional tables and PostgreSQL 16 RLS policies.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-22 21:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NEW_TENANT_TABLES = [
    "user_sessions",
    "organization_members",
    "meeting_settings",
    "source_segments",
    "voice_profiles",
    "meeting_chat",
    "outbox_events",
    "idempotency_keys",
]


def upgrade() -> None:
    # 1. Table: user_sessions
    op.create_table(
        "user_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("refresh_token_hash", sa.Text(), nullable=True),
        sa.Column("user_agent", sa.String(length=500), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
    op.create_index("idx_user_sessions_tenant_id", "user_sessions", ["tenant_id"])
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"])

    # 2. Table: organization_members
    op.create_table(
        "organization_members",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "role",
            sa.String(length=50),
            server_default="PARTICIPANT",
            nullable=False,
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
        sa.UniqueConstraint(
            "tenant_id", "user_id", name="uq_organization_members_tenant_user"
        ),
    )
    op.create_index("idx_org_members_tenant_id", "organization_members", ["tenant_id"])
    op.create_index("idx_org_members_user_id", "organization_members", ["user_id"])

    # 3. Table: meeting_settings
    op.create_table(
        "meeting_settings",
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
            unique=True,
        ),
        sa.Column("enable_recording", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("enable_transcription", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("enable_translation", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("enable_voice_cloning", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("retention_days", sa.Integer(), server_default=sa.text("30"), nullable=False),
        sa.Column("allowed_languages", sa.JSON(), nullable=False),
        sa.Column("extra_features", sa.JSON(), nullable=False),
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
    op.create_index("idx_meeting_settings_tenant_id", "meeting_settings", ["tenant_id"])
    op.create_index("idx_meeting_settings_meeting_id", "meeting_settings", ["meeting_id"])

    # 4. Table: source_segments (Invariant #2: Source Lineage Root)
    op.create_table(
        "source_segments",
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
        sa.Column("source_segment_id", sa.String(length=100), nullable=False, unique=True),
        sa.Column("speaker_id", sa.String(length=100), nullable=False),
        sa.Column("speaker_name", sa.String(length=100), nullable=False),
        sa.Column("language", sa.String(length=3), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
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
    op.create_index("idx_source_segments_tenant_id", "source_segments", ["tenant_id"])
    op.create_index("idx_source_segments_meeting_id", "source_segments", ["meeting_id"])
    op.create_index("idx_source_segments_lineage_id", "source_segments", ["source_segment_id"])

    # 5. Table: voice_profiles (pgvector 256 dimensions)
    op.execute(
        """
        CREATE TABLE voice_profiles (
            id UUID PRIMARY KEY,
            tenant_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            speaker_name VARCHAR(100) NOT NULL,
            embedding vector(256) NOT NULL,
            sample_rate INTEGER NOT NULL DEFAULT 16000,
            duration_sec FLOAT NOT NULL DEFAULT 0.0,
            is_verified BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.create_index("idx_voice_profiles_tenant_id", "voice_profiles", ["tenant_id"])
    op.create_index("idx_voice_profiles_user_id", "voice_profiles", ["user_id"])
    op.execute(
        """
        CREATE INDEX idx_voice_profiles_hnsw
        ON voice_profiles USING hnsw (embedding vector_cosine_ops);
        """
    )

    # 6. Table: meeting_chat
    op.create_table(
        "meeting_chat",
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
            "sender_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sender_name", sa.String(length=100), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=3), server_default="eng", nullable=False),
        sa.Column("translated_content", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_meeting_chat_tenant_id", "meeting_chat", ["tenant_id"])
    op.create_index("idx_meeting_chat_meeting_id", "meeting_chat", ["meeting_id"])

    # 7. Table: outbox_events (Transactional Outbox Pattern)
    op.create_table(
        "outbox_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_id", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("idx_outbox_events_tenant_id", "outbox_events", ["tenant_id"])
    op.create_index("idx_outbox_events_status", "outbox_events", ["is_published"])
    op.create_index("idx_outbox_events_event_type", "outbox_events", ["event_type"])

    # 8. Table: idempotency_keys (Replay Protection)
    op.create_table(
        "idempotency_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("target_endpoint", sa.String(length=255), nullable=False),
        sa.Column("response_code", sa.Integer(), nullable=True),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("tenant_id", "key", name="uq_idempotency_keys_tenant_key"),
    )
    op.create_index("idx_idempotency_keys_tenant_id", "idempotency_keys", ["tenant_id"])
    op.create_index("idx_idempotency_keys_lookup", "idempotency_keys", ["key"])

    # 9. Enforce PostgreSQL 16 RLS on all 8 tables
    for table in NEW_TENANT_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table} ON {table}
            USING (tenant_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            """
        )


def downgrade() -> None:
    for table in reversed(NEW_TENANT_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")

    op.drop_table("idempotency_keys")
    op.drop_table("outbox_events")
    op.drop_table("meeting_chat")
    op.drop_table("voice_profiles")
    op.drop_table("source_segments")
    op.drop_table("meeting_settings")
    op.drop_table("organization_members")
    op.drop_table("user_sessions")
