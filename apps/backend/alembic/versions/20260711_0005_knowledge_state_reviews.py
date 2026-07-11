"""Create knowledge state evidence and review queue.

Revision ID: 20260711_0005
Revises: 20260711_0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260711_0005"
down_revision: str | None = "20260711_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concept_evidence",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("evidence_type", sa.String(length=40), nullable=False),
        sa.Column("dimension", sa.String(length=40), nullable=False),
        sa.Column("score_delta", sa.Float(), nullable=False),
        sa.Column("strength", sa.Float(), nullable=False),
        sa.Column("source_type", sa.String(length=60), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "strength >= 0 AND strength <= 1",
            name=op.f("ck_concept_evidence_valid_strength"),
        ),
        sa.CheckConstraint(
            "evidence_type IN ('viewed', 'note_created', 'user_explanation', "
            "'review_answer', 'task_solved', 'applied_in_project', 'manual_adjustment')",
            name=op.f("ck_concept_evidence_valid_evidence_type"),
        ),
        sa.CheckConstraint(
            "dimension IN ('recall', 'explanation', 'structure', 'comparison', "
            "'application', 'hypothesis_generation', 'stability')",
            name=op.f("ck_concept_evidence_valid_dimension"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            name=op.f("fk_concept_evidence_concept_id_concepts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_concept_evidence_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_concept_evidence")),
    )
    op.create_index(op.f("ix_concept_evidence_concept_id"), "concept_evidence", ["concept_id"])
    op.create_index(op.f("ix_concept_evidence_user_id"), "concept_evidence", ["user_id"])
    op.create_index(
        "ix_concept_evidence_concept_occurred",
        "concept_evidence",
        ["concept_id", "occurred_at"],
    )

    op.create_table(
        "concept_states",
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("recall", sa.Float(), nullable=False),
        sa.Column("explanation", sa.Float(), nullable=False),
        sa.Column("structure", sa.Float(), nullable=False),
        sa.Column("comparison", sa.Float(), nullable=False),
        sa.Column("application", sa.Float(), nullable=False),
        sa.Column("hypothesis_generation", sa.Float(), nullable=False),
        sa.Column("stability", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("last_evidence_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "recall BETWEEN 0 AND 100 AND explanation BETWEEN 0 AND 100 AND "
            "structure BETWEEN 0 AND 100 AND comparison BETWEEN 0 AND 100 AND "
            "application BETWEEN 0 AND 100 AND hypothesis_generation BETWEEN 0 AND 100 "
            "AND stability BETWEEN 0 AND 100",
            name=op.f("ck_concept_states_valid_scores"),
        ),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1", name=op.f("ck_concept_states_valid_confidence")
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            name=op.f("fk_concept_states_concept_id_concepts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("concept_id", name=op.f("pk_concept_states")),
    )

    op.create_table(
        "review_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=False),
        sa.Column("review_type", sa.String(length=20), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "expected_points",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "review_type IN ('recall', 'explain', 'compare', 'apply', 'structure')",
            name=op.f("ck_review_items_valid_review_type"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'skipped')",
            name=op.f("ck_review_items_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            name=op.f("fk_review_items_concept_id_concepts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_items")),
    )
    op.create_index(op.f("ix_review_items_concept_id"), "review_items", ["concept_id"])
    op.create_index("ix_review_items_status_due", "review_items", ["status", "due_at"])

    op.create_table(
        "review_attempts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("review_item_id", sa.Uuid(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("self_rating", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "self_rating BETWEEN 1 AND 5",
            name=op.f("ck_review_attempts_valid_self_rating"),
        ),
        sa.CheckConstraint(
            "result IN ('failed', 'partial', 'passed')",
            name=op.f("ck_review_attempts_valid_result"),
        ),
        sa.ForeignKeyConstraint(
            ["review_item_id"],
            ["review_items.id"],
            name=op.f("fk_review_attempts_review_item_id_review_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_review_attempts")),
    )
    op.create_index(
        op.f("ix_review_attempts_review_item_id"),
        "review_attempts",
        ["review_item_id"],
    )


def downgrade() -> None:
    op.drop_table("review_attempts")
    op.drop_table("review_items")
    op.drop_table("concept_states")
    op.drop_table("concept_evidence")
