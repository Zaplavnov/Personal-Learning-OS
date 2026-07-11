from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from app.core.errors import ApiError
from app.modules.concepts.application import ConceptService
from app.modules.concepts.domain import ConceptRelationType
from app.modules.concepts.infrastructure import Concept, ConceptRelation
from app.modules.outbox.models import OutboxEvent

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_USER_ID = uuid4()
SPACE_ID = uuid4()
OTHER_SPACE_ID = uuid4()


class FakeConceptRepository:
    def __init__(self) -> None:
        self.owned_spaces = {USER_ID: {SPACE_ID, OTHER_SPACE_ID}}
        self.concepts: list[Concept] = []
        self.relations: list[ConceptRelation] = []
        self.pending: list[object] = []
        self.committed: list[list[object]] = []

    async def owns_space(self, user_id: UUID, space_id: UUID) -> bool:
        return space_id in self.owned_spaces.get(user_id, set())

    async def list_concepts(self, user_id, space_id, query):
        return [concept for concept in self.concepts if concept.user_id == user_id]

    async def get_concept(self, user_id: UUID, concept_id: UUID) -> Concept | None:
        return next(
            (
                concept
                for concept in self.concepts
                if concept.id == concept_id and concept.user_id == user_id
            ),
            None,
        )

    async def list_relations(self, user_id: UUID, space_id: UUID) -> list[ConceptRelation]:
        return [
            relation
            for relation in self.relations
            if relation.user_id == user_id and relation.learning_space_id == space_id
        ]

    async def get_relation(self, user_id: UUID, relation_id: UUID) -> ConceptRelation | None:
        return next(
            (
                relation
                for relation in self.relations
                if relation.id == relation_id and relation.user_id == user_id
            ),
            None,
        )

    async def find_relation(
        self, user_id: UUID, source_id: UUID, target_id: UUID, relation_type: str
    ) -> ConceptRelation | None:
        return next(
            (
                relation
                for relation in self.relations
                if relation.user_id == user_id
                and relation.source_concept_id == source_id
                and relation.target_concept_id == target_id
                and relation.relation_type == relation_type
            ),
            None,
        )

    def add(self, entity: object) -> None:
        self.pending.append(entity)
        if isinstance(entity, Concept):
            entity.created_at = entity.updated_at = datetime.now(UTC)
            entity.outgoing_relations = []
            entity.incoming_relations = []
            self.concepts.append(entity)
        elif isinstance(entity, ConceptRelation):
            entity.created_at = datetime.now(UTC)
            self.relations.append(entity)

    async def delete(self, entity: ConceptRelation) -> None:
        self.relations.remove(entity)

    async def commit(self) -> None:
        self.committed.append(list(self.pending))
        self.pending.clear()

    async def refresh(self, _entity: object) -> None:
        return None


def make_concept(
    repository: FakeConceptRepository,
    *,
    user_id: UUID = USER_ID,
    space_id: UUID = SPACE_ID,
) -> Concept:
    concept = Concept(
        id=uuid4(),
        user_id=user_id,
        learning_space_id=space_id,
        title=str(uuid4()),
        aliases=[],
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.concepts.append(concept)
    return concept


async def test_user_cannot_read_another_users_concept() -> None:
    repository = FakeConceptRepository()
    concept = make_concept(repository, user_id=OTHER_USER_ID)
    service = ConceptService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.get_concept(USER_ID, concept.id)

    assert error.value.code == "concept_not_found"


async def test_self_relation_is_rejected() -> None:
    repository = FakeConceptRepository()
    concept = make_concept(repository)
    service = ConceptService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.create_relation(
            USER_ID,
            source_concept_id=concept.id,
            target_concept_id=concept.id,
            relation_type=ConceptRelationType.PREREQUISITE_OF,
            description=None,
        )

    assert error.value.code == "concept_self_relation"


async def test_cross_space_relation_is_rejected() -> None:
    repository = FakeConceptRepository()
    source = make_concept(repository)
    target = make_concept(repository, space_id=OTHER_SPACE_ID)
    service = ConceptService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.create_relation(
            USER_ID,
            source_concept_id=source.id,
            target_concept_id=target.id,
            relation_type=ConceptRelationType.DEPENDS_ON,
            description=None,
        )

    assert error.value.code == "cross_space_concept_relation"


async def test_duplicate_relation_is_rejected() -> None:
    repository = FakeConceptRepository()
    source = make_concept(repository)
    target = make_concept(repository)
    service = ConceptService(repository)  # type: ignore[arg-type]
    await service.create_relation(
        USER_ID,
        source_concept_id=source.id,
        target_concept_id=target.id,
        relation_type=ConceptRelationType.EXPLAINS,
        description=None,
    )

    with pytest.raises(ApiError) as error:
        await service.create_relation(
            USER_ID,
            source_concept_id=source.id,
            target_concept_id=target.id,
            relation_type=ConceptRelationType.EXPLAINS,
            description=None,
        )

    assert error.value.code == "concept_relation_exists"


async def test_concept_and_outbox_event_share_commit() -> None:
    repository = FakeConceptRepository()
    service = ConceptService(repository)  # type: ignore[arg-type]

    concept = await service.create_concept(
        USER_ID,
        learning_space_id=SPACE_ID,
        title="Vectors",
        description=None,
        aliases=[],
    )

    transaction = repository.committed[-1]
    assert concept in transaction
    event = next(item for item in transaction if isinstance(item, OutboxEvent))
    assert event.event_type == "concept.created"
    assert event.aggregate_id == str(concept.id)
