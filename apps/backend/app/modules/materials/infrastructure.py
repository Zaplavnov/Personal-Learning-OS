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
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.common.models import TimestampMixin
from app.db.base import Base
from app.modules.learning_spaces.infrastructure import LearningSpace
from app.modules.materials.domain import (
    LearningSessionStatus,
    MaterialStatus,
    NoteType,
)
from app.modules.outbox.models import OutboxEvent
from app.modules.users.models import User


class Material(TimestampMixin, Base):
    __tablename__ = "materials"
    __table_args__ = (
        CheckConstraint(
            "type IN ('video', 'article', 'book', 'notebook', 'repository', 'other')",
            name="valid_type",
        ),
        CheckConstraint("status IN ('active', 'completed', 'archived')", name="valid_status"),
        CheckConstraint(
            "estimated_minutes IS NULL OR estimated_minutes >= 0",
            name="non_negative_estimated_minutes",
        ),
        Index("ix_materials_space_type", "learning_space_id", "type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_space_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    url: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=MaterialStatus.ACTIVE.value,
        server_default=MaterialStatus.ACTIVE.value,
    )
    estimated_minutes: Mapped[int | None] = mapped_column(Integer)
    material_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict, server_default=text("'{}'::jsonb")
    )
    sessions: Mapped[list["LearningSession"]] = relationship(
        back_populates="material",
        cascade="all, delete-orphan",
        order_by="LearningSession.started_at.desc()",
    )

    @property
    def active_session(self) -> "LearningSession | None":
        return next(
            (
                session
                for session in self.sessions
                if session.status == LearningSessionStatus.ACTIVE
            ),
            None,
        )


class LearningSession(Base):
    __tablename__ = "learning_sessions"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'abandoned')", name="valid_status"),
        CheckConstraint(
            "start_position_seconds IS NULL OR start_position_seconds >= 0",
            name="non_negative_start_position",
        ),
        CheckConstraint(
            "end_position_seconds IS NULL OR end_position_seconds >= 0",
            name="non_negative_end_position",
        ),
        Index(
            "uq_learning_sessions_one_active_per_user",
            "user_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    material_id: Mapped[UUID] = mapped_column(
        ForeignKey("materials.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    start_position_seconds: Mapped[int | None] = mapped_column(Integer)
    end_position_seconds: Mapped[int | None] = mapped_column(Integer)
    reflection: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=LearningSessionStatus.ACTIVE.value,
        server_default=LearningSessionStatus.ACTIVE.value,
    )
    material: Mapped[Material] = relationship(back_populates="sessions")


class Note(TimestampMixin, Base):
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint(
            "note_type IN ('insight', 'question', 'gap', 'example', 'general')",
            name="valid_note_type",
        ),
        CheckConstraint(
            "source_position_seconds IS NULL OR source_position_seconds >= 0",
            name="non_negative_source_position",
        ),
        Index("ix_notes_material_created_at", "material_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_space_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    material_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("materials.id", ondelete="SET NULL"), index=True
    )
    learning_session_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("learning_sessions.id", ondelete="SET NULL"), index=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    source_position_seconds: Mapped[int | None] = mapped_column(Integer)
    note_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=NoteType.GENERAL.value
    )


class SqlAlchemyMaterialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def owns_space(self, user_id: UUID, space_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(LearningSpace.id).where(
                    LearningSpace.id == space_id, LearningSpace.user_id == user_id
                )
            )
            is not None
        )

    async def lock_user(self, user_id: UUID) -> bool:
        return (
            await self.session.scalar(select(User.id).where(User.id == user_id).with_for_update())
            is not None
        )

    async def list_materials(
        self, user_id: UUID, space_id: UUID | None, material_type: str | None
    ) -> list[Material]:
        query = select(Material).where(Material.user_id == user_id)
        if space_id is not None:
            query = query.where(Material.learning_space_id == space_id)
        if material_type is not None:
            query = query.where(Material.type == material_type)
        return list(await self.session.scalars(query.order_by(Material.created_at.desc())))

    async def get_material(
        self, user_id: UUID, material_id: UUID, *, with_sessions: bool = False
    ) -> Material | None:
        query = select(Material).where(Material.id == material_id, Material.user_id == user_id)
        if with_sessions:
            query = query.options(selectinload(Material.sessions))
        return await self.session.scalar(query)

    async def get_session(self, user_id: UUID, session_id: UUID) -> LearningSession | None:
        return await self.session.scalar(
            select(LearningSession).where(
                LearningSession.id == session_id, LearningSession.user_id == user_id
            )
        )

    async def get_active_session(self, user_id: UUID) -> LearningSession | None:
        return await self.session.scalar(
            select(LearningSession).where(
                LearningSession.user_id == user_id,
                LearningSession.status == LearningSessionStatus.ACTIVE.value,
            )
        )

    async def get_note(self, user_id: UUID, note_id: UUID) -> Note | None:
        return await self.session.scalar(
            select(Note).where(Note.id == note_id, Note.user_id == user_id)
        )

    async def list_material_notes(self, user_id: UUID, material_id: UUID) -> list[Note]:
        return list(
            await self.session.scalars(
                select(Note)
                .where(Note.user_id == user_id, Note.material_id == material_id)
                .order_by(Note.created_at.desc())
            )
        )

    def add(self, entity: Material | LearningSession | Note | OutboxEvent) -> None:
        self.session.add(entity)

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, entity: Material | LearningSession | Note) -> None:
        await self.session.refresh(entity)
