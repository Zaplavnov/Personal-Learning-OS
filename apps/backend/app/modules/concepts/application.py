from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.modules.concepts.domain import ConceptRelationType, ConceptStatus
from app.modules.concepts.infrastructure import (
    Concept,
    ConceptRelation,
    SqlAlchemyConceptRepository,
)
from app.modules.outbox.models import OutboxEvent


class ConceptService:
    def __init__(self, repository: SqlAlchemyConceptRepository) -> None:
        self.repository = repository

    async def create_concept(
        self,
        user_id: UUID,
        *,
        learning_space_id: UUID,
        title: str,
        description: str | None,
        aliases: list[str],
    ) -> Concept:
        if not await self.repository.owns_space(user_id, learning_space_id):
            raise self._space_not_found()
        concept = Concept(
            id=uuid4(),
            user_id=user_id,
            learning_space_id=learning_space_id,
            title=title,
            description=description,
            aliases=aliases,
            status=ConceptStatus.ACTIVE.value,
        )
        self.repository.add(concept)
        self.repository.add(
            self._event("concept.created", "concept", concept.id, user_id, learning_space_id)
        )
        await self.repository.commit()
        await self.repository.refresh(concept)
        return concept

    async def list_concepts(
        self, user_id: UUID, space_id: UUID | None, query: str | None
    ) -> list[Concept]:
        return await self.repository.list_concepts(user_id, space_id, query)

    async def get_concept(self, user_id: UUID, concept_id: UUID) -> Concept:
        concept = await self.repository.get_concept(user_id, concept_id)
        if concept is None:
            raise self._concept_not_found()
        return concept

    async def update_concept(
        self, user_id: UUID, concept_id: UUID, changes: dict[str, object]
    ) -> Concept:
        concept = await self.get_concept(user_id, concept_id)
        for field, value in changes.items():
            if field == "status" and isinstance(value, ConceptStatus):
                value = value.value
            setattr(concept, field, value)
        await self.repository.commit()
        await self.repository.refresh(concept)
        return concept

    async def create_relation(
        self,
        user_id: UUID,
        *,
        source_concept_id: UUID,
        target_concept_id: UUID,
        relation_type: ConceptRelationType,
        description: str | None,
    ) -> ConceptRelation:
        if source_concept_id == target_concept_id:
            raise ApiError(
                "concept_self_relation",
                "A concept cannot be related to itself",
                status_code=422,
            )
        source = await self.repository.get_concept(user_id, source_concept_id)
        target = await self.repository.get_concept(user_id, target_concept_id)
        if source is None or target is None:
            raise self._concept_not_found()
        if source.learning_space_id != target.learning_space_id:
            raise ApiError(
                "cross_space_concept_relation",
                "Related concepts must belong to the same learning space",
                status_code=422,
            )
        if await self.repository.find_relation(user_id, source.id, target.id, relation_type.value):
            raise ApiError(
                "concept_relation_exists",
                "This concept relation already exists",
                status_code=409,
            )
        relation = ConceptRelation(
            id=uuid4(),
            user_id=user_id,
            learning_space_id=source.learning_space_id,
            source_concept_id=source.id,
            target_concept_id=target.id,
            relation_type=relation_type.value,
            description=description,
        )
        self.repository.add(relation)
        self.repository.add(
            self._event(
                "concept.relation_added",
                "concept_relation",
                relation.id,
                user_id,
                source.learning_space_id,
                {"source_concept_id": str(source.id), "target_concept_id": str(target.id)},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(relation)
        return relation

    async def delete_relation(self, user_id: UUID, relation_id: UUID) -> None:
        relation = await self.repository.get_relation(user_id, relation_id)
        if relation is None:
            raise ApiError(
                "concept_relation_not_found",
                "Concept relation was not found",
                status_code=404,
            )
        await self.repository.delete(relation)
        await self.repository.commit()

    async def get_graph(
        self, user_id: UUID, learning_space_id: UUID
    ) -> tuple[list[Concept], list[ConceptRelation]]:
        if not await self.repository.owns_space(user_id, learning_space_id):
            raise self._space_not_found()
        return (
            await self.repository.list_concepts(user_id, learning_space_id, None),
            await self.repository.list_relations(user_id, learning_space_id),
        )

    @staticmethod
    def _event(
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        user_id: UUID,
        learning_space_id: UUID,
        extra: dict[str, object] | None = None,
    ) -> OutboxEvent:
        return OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload={
                "user_id": str(user_id),
                "learning_space_id": str(learning_space_id),
                **(extra or {}),
            },
        )

    @staticmethod
    def _concept_not_found() -> ApiError:
        return ApiError("concept_not_found", "Concept was not found", status_code=404)

    @staticmethod
    def _space_not_found() -> ApiError:
        return ApiError("learning_space_not_found", "Learning space was not found", status_code=404)
