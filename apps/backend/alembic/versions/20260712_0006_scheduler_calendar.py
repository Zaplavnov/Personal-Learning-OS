"""Create scheduler calendar tables.

Revision ID: 20260712_0006
Revises: 20260711_0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260712_0006"
down_revision: str | None = "20260711_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "calendar_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=True),
        sa.Column("item_type", sa.String(length=30), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("planned_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="planned", nullable=False),
        sa.Column("flexibility", sa.String(length=20), server_default="flexible", nullable=False),
        sa.Column("priority", sa.Integer(), server_default="0", nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "item_type IN ('material_session', 'review', 'explain', 'practice', 'gap_work')",
            name=op.f("ck_calendar_items_valid_item_type"),
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'skipped')",
            name=op.f("ck_calendar_items_valid_status"),
        ),
        sa.CheckConstraint(
            "flexibility IN ('fixed', 'flexible')",
            name=op.f("ck_calendar_items_valid_flexibility"),
        ),
        sa.CheckConstraint(
            "estimated_minutes > 0",
            name=op.f("ck_calendar_items_positive_estimated_minutes"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_calendar_items_learning_space_id_learning_spaces"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_calendar_items_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_calendar_items")),
    )
    op.create_index(op.f("ix_calendar_items_user_id"), "calendar_items", ["user_id"])
    op.create_index(
        op.f("ix_calendar_items_learning_space_id"),
        "calendar_items",
        ["learning_space_id"],
    )
    op.create_index("ix_calendar_items_user_start", "calendar_items", ["user_id", "planned_start"])

    op.create_table(
        "schedule_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column(
            "snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_schedule_versions_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_schedule_versions")),
    )
    op.create_index(op.f("ix_schedule_versions_user_id"), "schedule_versions", ["user_id"])


def downgrade() -> None:
    op.drop_table("schedule_versions")
    op.drop_table("calendar_items")
