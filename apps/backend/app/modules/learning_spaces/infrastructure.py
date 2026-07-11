from datetime import date
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    and_,
    select,
    text,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.common.models import TimestampMixin
from app.db.base import Base
from app.modules.learning_spaces.domain import LearningGoalStatus, LearningSpaceStatus


class LearningSpace(TimestampMixin, Base):
    __tablename__ = "learning_spaces"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="valid_status"),
        Index("ix_learning_spaces_user_status", "user_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LearningSpaceStatus.ACTIVE.value,
        server_default=LearningSpaceStatus.ACTIVE.value,
    )
    goals: Mapped[list["LearningGoal"]] = relationship(
        back_populates="learning_space",
        cascade="all, delete-orphan",
        order_by="LearningGoal.priority.desc(), LearningGoal.created_at",
    )


class LearningGoal(TimestampMixin, Base):
    __tablename__ = "learning_goals"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'paused', 'completed')", name="valid_status"),
        Index("ix_learning_goals_space_status", "learning_space_id", "status"),
        Index(
            "uq_learning_goals_one_active_per_space",
            "learning_space_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    learning_space_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LearningGoalStatus.PAUSED.value,
        server_default=LearningGoalStatus.PAUSED.value,
    )
    target_date: Mapped[date | None] = mapped_column(Date)
    expected_capabilities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    completion_criteria: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    learning_space: Mapped[LearningSpace] = relationship(back_populates="goals")


class SqlAlchemyLearningSpaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_spaces(self, user_id: UUID) -> list[LearningSpace]:
        result = await self.session.scalars(
            select(LearningSpace)
            .where(LearningSpace.user_id == user_id)
            .options(selectinload(LearningSpace.goals))
            .order_by(LearningSpace.created_at)
        )
        return list(result.unique())

    async def get_space(self, user_id: UUID, space_id: UUID) -> LearningSpace | None:
        return await self.session.scalar(
            select(LearningSpace)
            .where(LearningSpace.id == space_id, LearningSpace.user_id == user_id)
            .options(selectinload(LearningSpace.goals))
        )

    async def lock_space(self, user_id: UUID, space_id: UUID) -> LearningSpace | None:
        return await self.session.scalar(
            select(LearningSpace)
            .where(LearningSpace.id == space_id, LearningSpace.user_id == user_id)
            .with_for_update()
        )

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> LearningGoal | None:
        return await self.session.scalar(
            select(LearningGoal)
            .join(LearningSpace)
            .where(LearningGoal.id == goal_id, LearningSpace.user_id == user_id)
        )

    async def pause_active_goals(self, space_id: UUID, except_goal_id: UUID | None = None) -> None:
        conditions = [
            LearningGoal.learning_space_id == space_id,
            LearningGoal.status == LearningGoalStatus.ACTIVE.value,
        ]
        if except_goal_id is not None:
            conditions.append(LearningGoal.id != except_goal_id)
        await self.session.execute(
            update(LearningGoal)
            .where(and_(*conditions))
            .values(status=LearningGoalStatus.PAUSED.value)
        )

    def add_space(self, space: LearningSpace) -> None:
        self.session.add(space)

    def add_goal(self, goal: LearningGoal) -> None:
        self.session.add(goal)

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh_space(self, space: LearningSpace) -> LearningSpace:
        refreshed = await self.get_space(space.user_id, space.id)
        if refreshed is None:
            raise RuntimeError("Learning space disappeared after commit")
        return refreshed

    async def refresh_goal(self, user_id: UUID, goal: LearningGoal) -> LearningGoal:
        refreshed = await self.get_goal(user_id, goal.id)
        if refreshed is None:
            raise RuntimeError("Learning goal disappeared after commit")
        return refreshed
