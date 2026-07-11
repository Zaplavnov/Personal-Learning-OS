from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from app.common.models import TimestampMixin
from app.db.base import Base
from app.modules.concepts.domain import ConceptStatus
from app.modules.learning_spaces.infrastructure import LearningSpace
from app.modules.outbox.models import OutboxEvent


class Concept(TimestampMixin, Base):
    __tablename__ = "concepts"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="valid_status"),
        UniqueConstraint("learning_space_id", "title", name="uq_concepts_space_title"),
        Index("ix_concepts_space_status", "learning_space_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_space_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb")
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=ConceptStatus.ACTIVE.value,
        server_default=ConceptStatus.ACTIVE.value,
    )
    outgoing_relations: Mapped[list["ConceptRelation"]] = relationship(
        foreign_keys="ConceptRelation.source_concept_id",
        back_populates="source_concept",
        cascade="all, delete-orphan",
    )
    incoming_relations: Mapped[list["ConceptRelation"]] = relationship(
        foreign_keys="ConceptRelation.target_concept_id",
        back_populates="target_concept",
        cascade="all, delete-orphan",
    )


class ConceptRelation(Base):
    __tablename__ = "concept_relations"
    __table_args__ = (
        CheckConstraint("source_concept_id <> target_concept_id", name="not_self_relation"),
        CheckConstraint(
            "relation_type IN ('prerequisite_of', 'depends_on', 'part_of', 'example_of', "
            "'generalization_of', 'special_case_of', 'contrasts_with', "
            "'often_confused_with', 'used_in', 'derived_from', 'analogous_to', "
            "'explains', 'implemented_by')",
            name="valid_relation_type",
        ),
        UniqueConstraint(
            "source_concept_id",
            "target_concept_id",
            "relation_type",
            name="uq_concept_relations_edge",
        ),
        Index("ix_concept_relations_space", "learning_space_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    learning_space_id: Mapped[UUID] = mapped_column(
        ForeignKey("learning_spaces.id", ondelete="CASCADE"), nullable=False
    )
    source_concept_id: Mapped[UUID] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_concept_id: Mapped[UUID] = mapped_column(
        ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    relation_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    source_concept: Mapped[Concept] = relationship(
        foreign_keys=[source_concept_id], back_populates="outgoing_relations"
    )
    target_concept: Mapped[Concept] = relationship(
        foreign_keys=[target_concept_id], back_populates="incoming_relations"
    )


class SqlAlchemyConceptRepository:
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

    async def list_concepts(
        self, user_id: UUID, space_id: UUID | None, query: str | None
    ) -> list[Concept]:
        statement = select(Concept).where(Concept.user_id == user_id)
        if space_id is not None:
            statement = statement.where(Concept.learning_space_id == space_id)
        if query:
            statement = statement.where(Concept.title.ilike(f"%{query}%"))
        return list(await self.session.scalars(statement.order_by(Concept.created_at)))

    async def get_concept(self, user_id: UUID, concept_id: UUID) -> Concept | None:
        return await self.session.scalar(
            select(Concept)
            .where(Concept.id == concept_id, Concept.user_id == user_id)
            .options(
                selectinload(Concept.outgoing_relations),
                selectinload(Concept.incoming_relations),
            )
        )

    async def list_relations(self, user_id: UUID, space_id: UUID) -> list[ConceptRelation]:
        return list(
            await self.session.scalars(
                select(ConceptRelation).where(
                    ConceptRelation.user_id == user_id,
                    ConceptRelation.learning_space_id == space_id,
                )
            )
        )

    async def get_relation(self, user_id: UUID, relation_id: UUID) -> ConceptRelation | None:
        return await self.session.scalar(
            select(ConceptRelation).where(
                ConceptRelation.id == relation_id, ConceptRelation.user_id == user_id
            )
        )

    async def find_relation(
        self,
        user_id: UUID,
        source_id: UUID,
        target_id: UUID,
        relation_type: str,
    ) -> ConceptRelation | None:
        return await self.session.scalar(
            select(ConceptRelation).where(
                ConceptRelation.user_id == user_id,
                ConceptRelation.source_concept_id == source_id,
                ConceptRelation.target_concept_id == target_id,
                ConceptRelation.relation_type == relation_type,
            )
        )

    def add(self, entity: Concept | ConceptRelation | OutboxEvent) -> None:
        self.session.add(entity)

    async def delete(self, entity: ConceptRelation) -> None:
        await self.session.delete(entity)

    async def commit(self) -> None:
        await self.session.commit()

    async def refresh(self, entity: Concept | ConceptRelation) -> None:
        await self.session.refresh(entity)
