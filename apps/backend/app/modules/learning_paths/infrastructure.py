from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    delete,
    func,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin
from app.db.base import Base
from app.modules.concepts.infrastructure import Concept, ConceptRelation
from app.modules.knowledge_state.infrastructure import ConceptEvidence, ConceptState
from app.modules.learning_paths.domain import (
    NodeImportance,
    NodeStatus,
    PathStatus,
    ResourceStatus,
    SuggestionStatus,
)
from app.modules.learning_spaces.infrastructure import LearningGoal, LearningSpace
from app.modules.materials.infrastructure import Material
from app.modules.outbox.models import OutboxEvent


class LearningPath(TimestampMixin, Base):
    __tablename__ = "learning_paths"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed', 'archived')",
            name="valid_status",
        ),
        Index(
            "uq_learning_paths_one_active_per_goal",
            "learning_goal_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_space_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_goal_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_goals.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=PathStatus.DRAFT.value, server_default="draft"
    )
    current_node_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "learning_path_nodes.id",
            ondelete="SET NULL",
            use_alter=True,
            name="fk_learning_paths_current_node_id_learning_path_nodes",
        )
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")


class LearningPathNode(TimestampMixin, Base):
    __tablename__ = "learning_path_nodes"
    __table_args__ = (
        CheckConstraint(
            "node_type IN ('concept', 'capability', 'milestone')", name="valid_node_type"
        ),
        CheckConstraint(
            "status IN ('planned', 'available', 'current', 'completed', 'blocked', 'skipped')",
            name="valid_status",
        ),
        CheckConstraint(
            "importance IN ('required', 'recommended', 'optional')", name="valid_importance"
        ),
        CheckConstraint(
            "node_type <> 'concept' OR concept_id IS NOT NULL",
            name="concept_node_requires_concept",
        ),
        Index("ix_learning_path_nodes_path_status", "learning_path_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    learning_path_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    concept_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("concepts.id", ondelete="RESTRICT"), index=True
    )
    node_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    position_x: Mapped[float | None] = mapped_column(Float)
    position_y: Mapped[float | None] = mapped_column(Float)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NodeStatus.PLANNED.value, server_default="planned"
    )
    importance: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=NodeImportance.REQUIRED.value,
        server_default="required",
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    completion_policy: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    node_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class LearningPathEdge(Base):
    __tablename__ = "learning_path_edges"
    __table_args__ = (
        CheckConstraint("source_node_id <> target_node_id", name="not_self_edge"),
        CheckConstraint(
            "edge_type IN ('sequence', 'prerequisite', 'optional_branch', "
            "'remediation', 'returns_to')",
            name="valid_edge_type",
        ),
        UniqueConstraint(
            "source_node_id", "target_node_id", "edge_type", name="uq_learning_path_edge"
        ),
        Index("ix_learning_path_edges_path", "learning_path_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    learning_path_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False
    )
    source_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_path_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_node_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_path_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    edge_type: Mapped[str] = mapped_column(String(30), nullable=False)
    condition: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    label: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class LearningPathNodeResource(TimestampMixin, Base):
    __tablename__ = "learning_path_node_resources"
    __table_args__ = (
        CheckConstraint(
            "resource_type IN ('material', 'review_template', 'practice', "
            "'explanation', 'project_task')",
            name="valid_resource_type",
        ),
        CheckConstraint(
            "completion_status IN ('planned', 'in_progress', 'completed', 'skipped')",
            name="valid_completion_status",
        ),
        Index("ix_learning_path_resources_node_order", "node_id", "order_index"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    node_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_path_nodes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    resource_id: Mapped[UUID | None] = mapped_column(index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ResourceStatus.PLANNED.value,
        server_default="planned",
    )
    resource_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )


class LearningPathSuggestion(Base):
    __tablename__ = "learning_path_suggestions"
    __table_args__ = (
        CheckConstraint(
            "suggestion_type IN ('add_node', 'add_branch', 'reorder', "
            "'attach_resource', 'mark_blocked', 'skip_node')",
            name="valid_suggestion_type",
        ),
        CheckConstraint(
            "source IN ('rule_engine', 'knowledge_state', 'user', 'llm')",
            name="valid_source",
        ),
        CheckConstraint(
            "status IN ('pending', 'accepted', 'rejected', 'expired')", name="valid_status"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    learning_path_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    suggestion_type: Mapped[str] = mapped_column(String(30), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SuggestionStatus.PENDING.value, server_default="pending"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class LearningPathVersion(Base):
    __tablename__ = "learning_path_versions"
    __table_args__ = (
        CheckConstraint(
            "change_source IN ('user', 'accepted_suggestion', 'system')",
            name="valid_change_source",
        ),
        UniqueConstraint("learning_path_id", "version", name="uq_learning_path_version"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    learning_path_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_paths.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    change_summary: Mapped[str] = mapped_column(String(500), nullable=False)
    change_source: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SqlAlchemyLearningPathRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> LearningGoal | None:
        return await self.session.scalar(
            select(LearningGoal)
            .join(LearningSpace)
            .where(LearningGoal.id == goal_id, LearningSpace.user_id == user_id)
        )

    async def get_goal_path(self, user_id: UUID, goal_id: UUID) -> LearningPath | None:
        return await self.session.scalar(
            select(LearningPath)
            .where(LearningPath.user_id == user_id, LearningPath.learning_goal_id == goal_id)
            .order_by(
                (LearningPath.status == PathStatus.ACTIVE.value).desc(),
                LearningPath.updated_at.desc(),
            )
            .limit(1)
        )

    async def get_path(
        self, user_id: UUID, path_id: UUID, *, lock: bool = False
    ) -> LearningPath | None:
        query = select(LearningPath).where(
            LearningPath.id == path_id, LearningPath.user_id == user_id
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def list_nodes(self, path_id: UUID) -> list[LearningPathNode]:
        return list(
            await self.session.scalars(
                select(LearningPathNode)
                .where(LearningPathNode.learning_path_id == path_id)
                .order_by(
                    LearningPathNode.position_x,
                    LearningPathNode.position_y,
                    LearningPathNode.created_at,
                )
            )
        )

    async def list_edges(self, path_id: UUID) -> list[LearningPathEdge]:
        return list(
            await self.session.scalars(
                select(LearningPathEdge)
                .where(LearningPathEdge.learning_path_id == path_id)
                .order_by(LearningPathEdge.created_at)
            )
        )

    async def list_resources(self, path_id: UUID) -> list[LearningPathNodeResource]:
        return list(
            await self.session.scalars(
                select(LearningPathNodeResource)
                .join(LearningPathNode)
                .where(LearningPathNode.learning_path_id == path_id)
                .order_by(LearningPathNodeResource.order_index, LearningPathNodeResource.created_at)
            )
        )

    async def list_suggestions(
        self, path_id: UUID, *, pending_only: bool = False
    ) -> list[LearningPathSuggestion]:
        query = select(LearningPathSuggestion).where(
            LearningPathSuggestion.learning_path_id == path_id
        )
        if pending_only:
            query = query.where(LearningPathSuggestion.status == SuggestionStatus.PENDING.value)
        return list(
            await self.session.scalars(query.order_by(LearningPathSuggestion.created_at.desc()))
        )

    async def list_versions(self, path_id: UUID) -> list[LearningPathVersion]:
        return list(
            await self.session.scalars(
                select(LearningPathVersion)
                .where(LearningPathVersion.learning_path_id == path_id)
                .order_by(LearningPathVersion.version.desc())
            )
        )

    async def get_version(self, path_id: UUID, version: int) -> LearningPathVersion | None:
        return await self.session.scalar(
            select(LearningPathVersion).where(
                LearningPathVersion.learning_path_id == path_id,
                LearningPathVersion.version == version,
            )
        )

    async def get_node(self, path_id: UUID, node_id: UUID) -> LearningPathNode | None:
        return await self.session.scalar(
            select(LearningPathNode).where(
                LearningPathNode.id == node_id, LearningPathNode.learning_path_id == path_id
            )
        )

    async def get_edge(self, path_id: UUID, edge_id: UUID) -> LearningPathEdge | None:
        return await self.session.scalar(
            select(LearningPathEdge).where(
                LearningPathEdge.id == edge_id, LearningPathEdge.learning_path_id == path_id
            )
        )

    async def get_resource(
        self, path_id: UUID, resource_id: UUID
    ) -> LearningPathNodeResource | None:
        return await self.session.scalar(
            select(LearningPathNodeResource)
            .join(LearningPathNode)
            .where(
                LearningPathNodeResource.id == resource_id,
                LearningPathNode.learning_path_id == path_id,
            )
        )

    async def get_suggestion(
        self, user_id: UUID, suggestion_id: UUID, *, lock: bool = False
    ) -> LearningPathSuggestion | None:
        query = (
            select(LearningPathSuggestion)
            .join(LearningPath)
            .where(
                LearningPathSuggestion.id == suggestion_id,
                LearningPath.user_id == user_id,
            )
        )
        if lock:
            query = query.with_for_update()
        return await self.session.scalar(query)

    async def list_concepts(self, user_id: UUID, space_id: UUID) -> list[Concept]:
        return list(
            await self.session.scalars(
                select(Concept).where(
                    Concept.user_id == user_id,
                    Concept.learning_space_id == space_id,
                    Concept.status == "active",
                )
            )
        )

    async def list_concept_relations(self, user_id: UUID, space_id: UUID) -> list[ConceptRelation]:
        return list(
            await self.session.scalars(
                select(ConceptRelation).where(
                    ConceptRelation.user_id == user_id,
                    ConceptRelation.learning_space_id == space_id,
                )
            )
        )

    async def list_materials(self, user_id: UUID, space_id: UUID) -> list[Material]:
        return list(
            await self.session.scalars(
                select(Material).where(
                    Material.user_id == user_id, Material.learning_space_id == space_id
                )
            )
        )

    async def owns_material(self, user_id: UUID, material_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(Material.id).where(Material.id == material_id, Material.user_id == user_id)
            )
            is not None
        )

    async def get_states(self, concept_ids: list[UUID]) -> dict[UUID, ConceptState]:
        if not concept_ids:
            return {}
        states = await self.session.scalars(
            select(ConceptState).where(ConceptState.concept_id.in_(concept_ids))
        )
        return {state.concept_id: state for state in states}

    async def evidence_counts(self, concept_id: UUID) -> dict[str, int]:
        rows = await self.session.execute(
            select(ConceptEvidence.evidence_type, func.count(ConceptEvidence.id))
            .where(ConceptEvidence.concept_id == concept_id)
            .group_by(ConceptEvidence.evidence_type)
        )
        return {evidence_type: count for evidence_type, count in rows}

    async def archive_active_path(self, goal_id: UUID, except_path_id: UUID) -> None:
        await self.session.execute(
            update(LearningPath)
            .where(
                LearningPath.learning_goal_id == goal_id,
                LearningPath.status == PathStatus.ACTIVE.value,
                LearningPath.id != except_path_id,
            )
            .values(status=PathStatus.ARCHIVED.value)
        )

    async def delete_graph(self, path_id: UUID) -> None:
        await self.session.execute(
            delete(LearningPathNode).where(LearningPathNode.learning_path_id == path_id)
        )

    def add(
        self,
        entity: LearningPath
        | LearningPathNode
        | LearningPathEdge
        | LearningPathNodeResource
        | LearningPathSuggestion
        | LearningPathVersion
        | OutboxEvent,
    ) -> None:
        self.session.add(entity)

    async def delete(self, entity: object) -> None:
        await self.session.delete(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, entity: object) -> None:
        await self.session.refresh(entity)
