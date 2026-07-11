from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.modules.concepts.infrastructure import Concept
from app.modules.knowledge_state.domain import ReviewStatus
from app.modules.outbox.models import OutboxEvent


class ConceptEvidence(Base):
    __tablename__ = "concept_evidence"
    __table_args__ = (
        CheckConstraint("strength >= 0 AND strength <= 1", name="valid_strength"),
        CheckConstraint(
            "evidence_type IN ('viewed', 'note_created', 'user_explanation', "
            "'review_answer', 'task_solved', 'applied_in_project', 'manual_adjustment')",
            name="valid_evidence_type",
        ),
        CheckConstraint(
            "dimension IN ('recall', 'explanation', 'structure', 'comparison', "
            "'application', 'hypothesis_generation', 'stability')",
            name="valid_dimension",
        ),
        Index("ix_concept_evidence_concept_occurred", "concept_id", "occurred_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    evidence_type: Mapped[str] = mapped_column(String(40), nullable=False)
    dimension: Mapped[str] = mapped_column(String(40), nullable=False)
    score_delta: Mapped[float] = mapped_column(Float, nullable=False)
    strength: Mapped[float] = mapped_column(Float, nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(100))
    evidence_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ConceptState(Base):
    __tablename__ = "concept_states"
    __table_args__ = (
        CheckConstraint(
            "recall BETWEEN 0 AND 100 AND explanation BETWEEN 0 AND 100 AND "
            "structure BETWEEN 0 AND 100 AND comparison BETWEEN 0 AND 100 AND "
            "application BETWEEN 0 AND 100 AND hypothesis_generation BETWEEN 0 AND 100 "
            "AND stability BETWEEN 0 AND 100",
            name="valid_scores",
        ),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="valid_confidence"),
    )

    concept_id: Mapped[UUID] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True
    )
    recall: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    explanation: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    structure: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    comparison: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    application: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    hypothesis_generation: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    stability: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    last_evidence_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ReviewItem(Base):
    __tablename__ = "review_items"
    __table_args__ = (
        CheckConstraint(
            "review_type IN ('recall', 'explain', 'compare', 'apply', 'structure')",
            name="valid_review_type",
        ),
        CheckConstraint("status IN ('pending', 'completed', 'skipped')", name="valid_status"),
        Index("ix_review_items_status_due", "status", "due_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    concept_id: Mapped[UUID] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    review_type: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    expected_points: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ReviewStatus.PENDING.value,
        server_default=ReviewStatus.PENDING.value,
    )
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class ReviewAttempt(Base):
    __tablename__ = "review_attempts"
    __table_args__ = (
        CheckConstraint("self_rating BETWEEN 1 AND 5", name="valid_self_rating"),
        CheckConstraint("result IN ('failed', 'partial', 'passed')", name="valid_result"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    review_item_id: Mapped[UUID] = mapped_column(
        ForeignKey("review_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    self_rating: Mapped[int] = mapped_column(Integer, nullable=False)
    result: Mapped[str] = mapped_column(String(20), nullable=False)
    feedback: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SqlAlchemyKnowledgeStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_concept(self, user_id: UUID, concept_id: UUID) -> Concept | None:
        return await self.session.scalar(
            select(Concept).where(Concept.id == concept_id, Concept.user_id == user_id)
        )

    async def list_evidence(self, user_id: UUID, concept_id: UUID) -> list[ConceptEvidence]:
        return list(
            await self.session.scalars(
                select(ConceptEvidence)
                .where(
                    ConceptEvidence.user_id == user_id,
                    ConceptEvidence.concept_id == concept_id,
                )
                .order_by(ConceptEvidence.occurred_at, ConceptEvidence.id)
            )
        )

    async def get_state(self, concept_id: UUID) -> ConceptState | None:
        return await self.session.get(ConceptState, concept_id)

    async def get_review(self, user_id: UUID, review_id: UUID) -> ReviewItem | None:
        return await self.session.scalar(
            select(ReviewItem)
            .join(Concept)
            .where(ReviewItem.id == review_id, Concept.user_id == user_id)
            .with_for_update()
        )

    async def list_due_reviews(self, user_id: UUID, now: datetime) -> list[ReviewItem]:
        return list(
            await self.session.scalars(
                select(ReviewItem)
                .join(Concept)
                .where(
                    Concept.user_id == user_id,
                    ReviewItem.status == ReviewStatus.PENDING.value,
                    ReviewItem.due_at <= now,
                )
                .order_by(ReviewItem.due_at)
            )
        )

    async def next_pending_review_at(self, concept_id: UUID) -> datetime | None:
        return await self.session.scalar(
            select(ReviewItem.due_at)
            .where(
                ReviewItem.concept_id == concept_id,
                ReviewItem.status == ReviewStatus.PENDING.value,
            )
            .order_by(ReviewItem.due_at)
            .limit(1)
        )

    def add(
        self,
        entity: ConceptEvidence | ConceptState | ReviewItem | ReviewAttempt | OutboxEvent,
    ) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, entity: ConceptEvidence | ConceptState | ReviewItem) -> None:
        await self.session.refresh(entity)
