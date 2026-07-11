"""Create materials, learning sessions, and notes.

Revision ID: 20260711_0003
Revises: 20260711_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260711_0003"
down_revision: str | None = "20260711_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def timestamp_columns() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:
    op.create_table(
        "materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("author", sa.String(length=300), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *timestamp_columns(),
        sa.CheckConstraint(
            "type IN ('video', 'article', 'book', 'notebook', 'repository', 'other')",
            name=op.f("ck_materials_valid_type"),
        ),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name=op.f("ck_materials_valid_status"),
        ),
        sa.CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes >= 0",
            name=op.f("ck_materials_non_negative_estimated_minutes"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_materials_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_materials_learning_space_id_learning_spaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_materials")),
    )
    op.create_index(op.f("ix_materials_user_id"), "materials", ["user_id"])
    op.create_index(op.f("ix_materials_learning_space_id"), "materials", ["learning_space_id"])
    op.create_index("ix_materials_space_type", "materials", ["learning_space_id", "type"])

    op.create_table(
        "learning_sessions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_position_seconds", sa.Integer(), nullable=True),
        sa.Column("end_position_seconds", sa.Integer(), nullable=True),
        sa.Column("reflection", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
        sa.CheckConstraint(
            "status IN ('active', 'completed', 'abandoned')",
            name=op.f("ck_learning_sessions_valid_status"),
        ),
        sa.CheckConstraint(
            "start_position_seconds IS NULL OR start_position_seconds >= 0",
            name=op.f("ck_learning_sessions_non_negative_start_position"),
        ),
        sa.CheckConstraint(
            "end_position_seconds IS NULL OR end_position_seconds >= 0",
            name=op.f("ck_learning_sessions_non_negative_end_position"),
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name=op.f("fk_learning_sessions_material_id_materials"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_learning_sessions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_sessions")),
    )
    op.create_index(op.f("ix_learning_sessions_material_id"), "learning_sessions", ["material_id"])
    op.create_index(op.f("ix_learning_sessions_user_id"), "learning_sessions", ["user_id"])
    op.create_index(
        "uq_learning_sessions_one_active_per_user",
        "learning_sessions",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=False),
        sa.Column("material_id", sa.Uuid(), nullable=True),
        sa.Column("learning_session_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("source_position_seconds", sa.Integer(), nullable=True),
        sa.Column("note_type", sa.String(length=20), nullable=False),
        *timestamp_columns(),
        sa.CheckConstraint(
            "note_type IN ('insight', 'question', 'gap', 'example', 'general')",
            name=op.f("ck_notes_valid_note_type"),
        ),
        sa.CheckConstraint(
            "source_position_seconds IS NULL OR source_position_seconds >= 0",
            name=op.f("ck_notes_non_negative_source_position"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_notes_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_notes_learning_space_id_learning_spaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["material_id"],
            ["materials.id"],
            name=op.f("fk_notes_material_id_materials"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["learning_session_id"],
            ["learning_sessions.id"],
            name=op.f("fk_notes_learning_session_id_learning_sessions"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
    )
    op.create_index(op.f("ix_notes_user_id"), "notes", ["user_id"])
    op.create_index(op.f("ix_notes_learning_space_id"), "notes", ["learning_space_id"])
    op.create_index(op.f("ix_notes_material_id"), "notes", ["material_id"])
    op.create_index(op.f("ix_notes_learning_session_id"), "notes", ["learning_session_id"])
    op.create_index("ix_notes_material_created_at", "notes", ["material_id", "created_at"])


def downgrade() -> None:
    op.drop_table("notes")
    op.drop_table("learning_sessions")
    op.drop_table("materials")
