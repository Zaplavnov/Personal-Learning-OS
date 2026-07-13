"""Create collaboratively configurable learning paths.

Revision ID: 20260712_0007
Revises: 20260712_0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260712_0007"
down_revision: str | None = "20260712_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "learning_paths",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("learning_space_id", sa.Uuid(), nullable=False),
        sa.Column("learning_goal_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("current_node_id", sa.Uuid(), nullable=True),
        sa.Column("version", sa.Integer(), server_default="0", nullable=False),
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
            "status IN ('draft', 'active', 'paused', 'completed', 'archived')",
            name=op.f("ck_learning_paths_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_goal_id"],
            ["learning_goals.id"],
            name=op.f("fk_learning_paths_learning_goal_id_learning_goals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["learning_space_id"],
            ["learning_spaces.id"],
            name=op.f("fk_learning_paths_learning_space_id_learning_spaces"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_learning_paths_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_paths")),
    )
    op.create_index(op.f("ix_learning_paths_user_id"), "learning_paths", ["user_id"])
    op.create_index(
        op.f("ix_learning_paths_learning_space_id"), "learning_paths", ["learning_space_id"]
    )
    op.create_index(
        op.f("ix_learning_paths_learning_goal_id"), "learning_paths", ["learning_goal_id"]
    )
    op.create_index(
        "uq_learning_paths_one_active_per_goal",
        "learning_paths",
        ["learning_goal_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "learning_path_nodes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("concept_id", sa.Uuid(), nullable=True),
        sa.Column("node_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=True),
        sa.Column("position_y", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="planned", nullable=False),
        sa.Column("importance", sa.String(length=20), server_default="required", nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column(
            "completion_policy",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "metadata",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "node_type IN ('concept', 'capability', 'milestone')",
            name=op.f("ck_learning_path_nodes_valid_node_type"),
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'available', 'current', 'completed', 'blocked', 'skipped')",
            name=op.f("ck_learning_path_nodes_valid_status"),
        ),
        sa.CheckConstraint(
            "importance IN ('required', 'recommended', 'optional')",
            name=op.f("ck_learning_path_nodes_valid_importance"),
        ),
        sa.CheckConstraint(
            "node_type <> 'concept' OR concept_id IS NOT NULL",
            name=op.f("ck_learning_path_nodes_concept_node_requires_concept"),
        ),
        sa.ForeignKeyConstraint(
            ["concept_id"],
            ["concepts.id"],
            name=op.f("fk_learning_path_nodes_concept_id_concepts"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["learning_path_id"],
            ["learning_paths.id"],
            name=op.f("fk_learning_path_nodes_learning_path_id_learning_paths"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_path_nodes")),
    )
    op.create_index(
        op.f("ix_learning_path_nodes_learning_path_id"), "learning_path_nodes", ["learning_path_id"]
    )
    op.create_index(
        op.f("ix_learning_path_nodes_concept_id"), "learning_path_nodes", ["concept_id"]
    )
    op.create_index(
        "ix_learning_path_nodes_path_status", "learning_path_nodes", ["learning_path_id", "status"]
    )
    op.create_foreign_key(
        "fk_learning_paths_current_node_id_learning_path_nodes",
        "learning_paths",
        "learning_path_nodes",
        ["current_node_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "learning_path_edges",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("source_node_id", sa.Uuid(), nullable=False),
        sa.Column("target_node_id", sa.Uuid(), nullable=False),
        sa.Column("edge_type", sa.String(length=30), nullable=False),
        sa.Column("condition", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("label", sa.String(length=200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source_node_id <> target_node_id", name=op.f("ck_learning_path_edges_not_self_edge")
        ),
        sa.CheckConstraint(
            "edge_type IN ('sequence', 'prerequisite', 'optional_branch', "
            "'remediation', 'returns_to')",
            name=op.f("ck_learning_path_edges_valid_edge_type"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_path_id"],
            ["learning_paths.id"],
            name=op.f("fk_learning_path_edges_learning_path_id_learning_paths"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["source_node_id"],
            ["learning_path_nodes.id"],
            name=op.f("fk_learning_path_edges_source_node_id_learning_path_nodes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_node_id"],
            ["learning_path_nodes.id"],
            name=op.f("fk_learning_path_edges_target_node_id_learning_path_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_path_edges")),
        sa.UniqueConstraint(
            "source_node_id", "target_node_id", "edge_type", name=op.f("uq_learning_path_edge")
        ),
    )
    op.create_index(
        op.f("ix_learning_path_edges_source_node_id"), "learning_path_edges", ["source_node_id"]
    )
    op.create_index(
        op.f("ix_learning_path_edges_target_node_id"), "learning_path_edges", ["target_node_id"]
    )
    op.create_index("ix_learning_path_edges_path", "learning_path_edges", ["learning_path_id"])

    op.create_table(
        "learning_path_node_resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("node_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=30), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("is_required", sa.Boolean(), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False),
        sa.Column(
            "completion_status", sa.String(length=20), server_default="planned", nullable=False
        ),
        sa.Column(
            "metadata",
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
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "resource_type IN ('material', 'review_template', 'practice', "
            "'explanation', 'project_task')",
            name=op.f("ck_learning_path_node_resources_valid_resource_type"),
        ),
        sa.CheckConstraint(
            "completion_status IN ('planned', 'in_progress', 'completed', 'skipped')",
            name=op.f("ck_learning_path_node_resources_valid_completion_status"),
        ),
        sa.ForeignKeyConstraint(
            ["node_id"],
            ["learning_path_nodes.id"],
            name=op.f("fk_learning_path_node_resources_node_id_learning_path_nodes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_path_node_resources")),
    )
    op.create_index(
        op.f("ix_learning_path_node_resources_node_id"), "learning_path_node_resources", ["node_id"]
    )
    op.create_index(
        op.f("ix_learning_path_node_resources_resource_id"),
        "learning_path_node_resources",
        ["resource_id"],
    )
    op.create_index(
        "ix_learning_path_resources_node_order",
        "learning_path_node_resources",
        ["node_id", "order_index"],
    )

    op.create_table(
        "learning_path_suggestions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("suggestion_type", sa.String(length=30), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="pending", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "suggestion_type IN ('add_node', 'add_branch', 'reorder', "
            "'attach_resource', 'mark_blocked', 'skip_node')",
            name=op.f("ck_learning_path_suggestions_valid_suggestion_type"),
        ),
        sa.CheckConstraint(
            "source IN ('rule_engine', 'knowledge_state', 'user', 'llm')",
            name=op.f("ck_learning_path_suggestions_valid_source"),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired')",
            name=op.f("ck_learning_path_suggestions_valid_status"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_path_id"],
            ["learning_paths.id"],
            name=op.f("fk_learning_path_suggestions_learning_path_id_learning_paths"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_path_suggestions")),
    )
    op.create_index(
        op.f("ix_learning_path_suggestions_learning_path_id"),
        "learning_path_suggestions",
        ["learning_path_id"],
    )

    op.create_table(
        "learning_path_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("learning_path_id", sa.Uuid(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("change_summary", sa.String(length=500), nullable=False),
        sa.Column("change_source", sa.String(length=30), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "change_source IN ('user', 'accepted_suggestion', 'system')",
            name=op.f("ck_learning_path_versions_valid_change_source"),
        ),
        sa.ForeignKeyConstraint(
            ["learning_path_id"],
            ["learning_paths.id"],
            name=op.f("fk_learning_path_versions_learning_path_id_learning_paths"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_path_versions")),
        sa.UniqueConstraint("learning_path_id", "version", name=op.f("uq_learning_path_version")),
    )
    op.create_index(
        op.f("ix_learning_path_versions_learning_path_id"),
        "learning_path_versions",
        ["learning_path_id"],
    )


def downgrade() -> None:
    op.drop_table("learning_path_versions")
    op.drop_table("learning_path_suggestions")
    op.drop_table("learning_path_node_resources")
    op.drop_table("learning_path_edges")
    op.drop_constraint(
        "fk_learning_paths_current_node_id_learning_path_nodes",
        "learning_paths",
        type_="foreignkey",
    )
    op.drop_table("learning_path_nodes")
    op.drop_table("learning_paths")
