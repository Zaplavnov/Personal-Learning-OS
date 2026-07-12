from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    exists,
    func,
    or_,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.common.models import TimestampMixin
from app.db.base import Base
from app.modules.concepts.infrastructure import Concept, ConceptRelation
from app.modules.knowledge_state.infrastructure import ConceptState, ReviewItem
from app.modules.learning_spaces.infrastructure import LearningGoal, LearningSpace
from app.modules.materials.infrastructure import LearningSession, Material, Note
from app.modules.scheduler.domain import (
    ActiveContext,
    ActiveSessionInput,
    DueReviewInput,
    LowConceptInput,
    MaterialInput,
    OpenGapInput,
    SchedulerInputs,
)


class CalendarItem(TimestampMixin, Base):
    __tablename__ = "calendar_items"
    __table_args__ = (
        CheckConstraint(
            "item_type IN ('material_session', 'review', 'explain', 'practice', 'gap_work')",
            name="valid_item_type",
        ),
        CheckConstraint(
            "status IN ('planned', 'in_progress', 'completed', 'skipped')", name="valid_status"
        ),
        CheckConstraint("flexibility IN ('fixed', 'flexible')", name="valid_flexibility"),
        CheckConstraint("estimated_minutes > 0", name="positive_estimated_minutes"),
        Index("ix_calendar_items_user_start", "user_id", "planned_start"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_space_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="SET NULL"), index=True
    )
    item_type: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_id: Mapped[UUID | None] = mapped_column(nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    planned_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="planned")
    flexibility: Mapped[str] = mapped_column(String(20), nullable=False, server_default="flexible")
    priority: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    rationale: Mapped[str] = mapped_column(Text, nullable=False)


class ScheduleVersion(Base):
    __tablename__ = "schedule_versions"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    reason: Mapped[str] = mapped_column(String(200), nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class SqlAlchemySchedulerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def load_inputs(self, user_id: UUID, now: datetime) -> SchedulerInputs:
        goal_row = (
            await self.session.execute(
                select(LearningSpace.id, LearningSpace.title, LearningGoal.id, LearningGoal.title)
                .join(LearningGoal)
                .where(
                    LearningSpace.user_id == user_id,
                    LearningSpace.status == "active",
                    LearningGoal.status == "active",
                )
                .order_by(LearningGoal.priority.desc(), LearningGoal.created_at)
                .limit(1)
            )
        ).first()
        if goal_row:
            context = ActiveContext(goal_row[0], goal_row[1], goal_row[2], goal_row[3])
        else:
            space_row = (
                await self.session.execute(
                    select(LearningSpace.id, LearningSpace.title)
                    .where(LearningSpace.user_id == user_id, LearningSpace.status == "active")
                    .order_by(LearningSpace.created_at)
                    .limit(1)
                )
            ).first()
            context = ActiveContext(space_row[0], space_row[1]) if space_row else ActiveContext()

        review_rows = await self.session.execute(
            select(ReviewItem, Concept)
            .join(Concept, Concept.id == ReviewItem.concept_id)
            .where(
                Concept.user_id == user_id, ReviewItem.status == "pending", ReviewItem.due_at <= now
            )
            .order_by(ReviewItem.due_at)
        )
        due_reviews = tuple(
            DueReviewInput(
                review.id,
                concept.id,
                concept.learning_space_id,
                concept.title,
                review.review_type,
                review.prompt,
                review.due_at,
            )
            for review, concept in review_rows
        )
        session_rows = await self.session.execute(
            select(LearningSession, Material)
            .join(Material, Material.id == LearningSession.material_id)
            .where(LearningSession.user_id == user_id, LearningSession.status == "active")
        )
        active_sessions = tuple(
            ActiveSessionInput(
                session.id,
                material.id,
                material.learning_space_id,
                material.title,
                material.estimated_minutes,
            )
            for session, material in session_rows
        )
        prerequisite_ids = set(
            await self.session.scalars(
                select(ConceptRelation.source_concept_id).where(
                    ConceptRelation.user_id == user_id,
                    ConceptRelation.relation_type == "prerequisite_of",
                )
            )
        )
        concept_rows = await self.session.execute(
            select(Concept, ConceptState)
            .join(ConceptState, ConceptState.concept_id == Concept.id)
            .where(
                Concept.user_id == user_id,
                Concept.status == "active",
                or_(ConceptState.explanation < 50, ConceptState.application < 50),
            )
            .order_by(func.least(ConceptState.explanation, ConceptState.application), Concept.title)
        )
        low_concepts = tuple(
            LowConceptInput(
                concept.id,
                concept.learning_space_id,
                concept.title,
                state.explanation,
                state.application,
                concept.id in prerequisite_ids,
            )
            for concept, state in concept_rows
        )
        gap_rows = await self.session.scalars(
            select(Note)
            .where(
                Note.user_id == user_id,
                Note.note_type.in_(("gap", "question")),
                ~exists().where(
                    CalendarItem.user_id == user_id,
                    CalendarItem.source_type == "note",
                    CalendarItem.source_id == Note.id,
                    CalendarItem.status == "completed",
                ),
            )
            .order_by(Note.created_at.desc())
        )
        open_gaps = tuple(
            OpenGapInput(
                note.id, note.learning_space_id, note.material_id, note.body, note.note_type
            )
            for note in gap_rows
        )
        material_rows = await self.session.scalars(
            select(Material)
            .where(Material.user_id == user_id, Material.status == "active")
            .order_by(Material.created_at)
        )
        materials = tuple(
            MaterialInput(
                material.id, material.learning_space_id, material.title, material.estimated_minutes
            )
            for material in material_rows
        )
        summary = (
            await self.session.execute(
                select(
                    func.avg(ConceptState.stability),
                    func.avg(ConceptState.confidence),
                    func.count(ConceptState.concept_id),
                )
                .join(Concept, Concept.id == ConceptState.concept_id)
                .where(Concept.user_id == user_id)
            )
        ).one()
        return SchedulerInputs(
            context=context,
            due_reviews=due_reviews,
            active_sessions=active_sessions,
            low_concepts=low_concepts,
            open_gaps=open_gaps,
            materials=materials,
            average_stability=float(summary[0] or 0),
            average_confidence=float(summary[1] or 0),
            state_count=int(summary[2] or 0),
        )

    async def list_calendar(
        self, user_id: UUID, from_at: datetime, to_at: datetime
    ) -> list[CalendarItem]:
        return list(
            await self.session.scalars(
                select(CalendarItem)
                .where(
                    CalendarItem.user_id == user_id,
                    CalendarItem.planned_start >= from_at,
                    CalendarItem.planned_start < to_at,
                )
                .order_by(CalendarItem.planned_start, CalendarItem.priority.desc())
            )
        )

    async def get_item(self, user_id: UUID, item_id: UUID) -> CalendarItem | None:
        return await self.session.scalar(
            select(CalendarItem)
            .where(CalendarItem.id == item_id, CalendarItem.user_id == user_id)
            .with_for_update()
        )

    async def list_flexible_planned(
        self, user_id: UUID, from_at: datetime, to_at: datetime
    ) -> list[CalendarItem]:
        return list(
            await self.session.scalars(
                select(CalendarItem).where(
                    CalendarItem.user_id == user_id,
                    CalendarItem.planned_start >= from_at,
                    CalendarItem.planned_start < to_at,
                    CalendarItem.flexibility == "flexible",
                    CalendarItem.status == "planned",
                )
            )
        )

    def add(self, entity: CalendarItem | ScheduleVersion) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, item: CalendarItem) -> None:
        await self.session.refresh(item)
