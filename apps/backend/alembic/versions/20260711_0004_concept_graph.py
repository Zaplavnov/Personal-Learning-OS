"""Create concepts and concept relations.

Revision ID: 20260711_0004
Revises: 20260711_0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260711_0004"
down_revision: str | None = "20260711_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "concepts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "aliases",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
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
            "status IN ('active', 'archived')", name=op.f("ck_concepts_valid_status")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_concepts_user_id_users"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_concepts_learning_space_id_learning_spaces"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_concepts")),
        sa.UniqueConstraint("learning_space_id", "title", name=op.f("uq_concepts_space_title")),
    )
    op.create_index(op.f("ix_concepts_user_id"), "concepts", ["user_id"])
    op.create_index(op.f("ix_concepts_learning_space_id"), "concepts", ["learning_space_id"])
    op.create_index("ix_concepts_space_status", "concepts", ["learning_space_id", "status"])

    op.create_table(
        "concept_relations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=False),
        sa.Column("source_concept_id", sa.Uuid(), nullable=False),
        sa.Column("target_concept_id", sa.Uuid(), nullable=False),
        sa.Column("relation_type", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_concept_id <> target_concept_id",
            name=op.f("ck_concept_relations_not_self_relation"),
        ),
        sa.CheckConstraint(
            "relation_type IN ('prerequisite_of', 'depends_on', 'part_of', 'example_of', "
            "'generalization_of', 'special_case_of', 'contrasts_with', "
            "'often_confused_with', 'used_in', 'derived_from', 'analogous_to', "
            "'explains', 'implemented_by')",
            name=op.f("ck_concept_relations_valid_relation_type"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_concept_relations_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_concept_relations_learning_space_id_learning_spaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_concept_id"],
            ["concepts.id"],
            name=op.f("fk_concept_relations_source_concept_id_concepts"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_concept_id"],
            ["concepts.id"],
            name=op.f("fk_concept_relations_target_concept_id_concepts"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_concept_relations")),
        sa.UniqueConstraint(
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name=op.f("uq_concept_relations_edge"),
        ),
    )
    op.create_index(op.f("ix_concept_relations_user_id"), "concept_relations", ["user_id"])
    op.create_index(
        op.f("ix_concept_relations_source_concept_id"),
        "concept_relations",
        ["source_concept_id"],
    )
    op.create_index(
        op.f("ix_concept_relations_target_concept_id"),
        "concept_relations",
        ["target_concept_id"],
    )
    op.create_index("ix_concept_relations_space", "concept_relations", ["learning_space_id"])


def downgrade() -> None:
    op.drop_table("concept_relations")
    op.drop_table("concepts")
