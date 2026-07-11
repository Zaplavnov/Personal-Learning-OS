"""Create learning spaces and learning goals.

Revision ID: 20260711_0002
Revises: 20260711_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260711_0002"
down_revision: str | None = "20260711_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_spaces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("color", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="active", nullable=False),
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
            "status IN ('active', 'archived')", name=op.f("ck_learning_spaces_valid_status")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_learning_spaces_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_spaces")),
    )
    op.create_index(op.f("ix_learning_spaces_user_id"), "learning_spaces", ["user_id"])
    op.create_index("ix_learning_spaces_user_status", "learning_spaces", ["user_id", "status"])

    op.create_table(
        "learning_goals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="paused", nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column(
            "expected_capabilities",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "completion_criteria",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
            "status IN ('active', 'paused', 'completed')",
            name=op.f("ck_learning_goals_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_learning_goals_learning_space_id_learning_spaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_goals")),
    )
    op.create_index(
        op.f("ix_learning_goals_learning_space_id"),
        "learning_goals",
        ["learning_space_id"],
    )
    op.create_index(
        "ix_learning_goals_space_status", "learning_goals", ["learning_space_id", "status"]
    )
    op.create_index(
        "uq_learning_goals_one_active_per_space",
        "learning_goals",
        ["learning_space_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )


def downgrade() -> None:
    op.drop_index("uq_learning_goals_one_active_per_space", table_name="learning_goals")
    op.drop_index("ix_learning_goals_space_status", table_name="learning_goals")
    op.drop_index(op.f("ix_learning_goals_learning_space_id"), table_name="learning_goals")
    op.drop_table("learning_goals")
    op.drop_index("ix_learning_spaces_user_status", table_name="learning_spaces")
    op.drop_index(op.f("ix_learning_spaces_user_id"), table_name="learning_spaces")
    op.drop_table("learning_spaces")
