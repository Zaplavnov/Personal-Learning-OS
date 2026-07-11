from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient

from app.core.errors import ApiError
from app.modules.materials.application import MaterialService
from app.modules.materials.domain import LearningSessionStatus, MaterialType, NoteType
from app.modules.materials.infrastructure import LearningSession, Material, Note
from app.modules.outbox.models import OutboxEvent

USER_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_USER_ID = uuid4()
SPACE_ID = uuid4()
OTHER_SPACE_ID = uuid4()


class FakeMaterialRepository:
    def __init__(self) -> None:
        self.owned_spaces = {USER_ID: {SPACE_ID, OTHER_SPACE_ID}}
        self.materials: list[Material] = []
        self.sessions: list[LearningSession] = []
        self.notes: list[Note] = []
        self.pending: list[object] = []
        self.committed: list[list[object]] = []

    async def owns_space(self, user_id: UUID, space_id: UUID) -> bool:
        return space_id in self.owned_spaces.get(user_id, set())

    async def lock_user(self, _user_id: UUID) -> bool:
        return True

    async def list_materials(self, user_id, space_id, material_type):
        return [material for material in self.materials if material.user_id == user_id]

    async def get_material(
        self, user_id: UUID, material_id: UUID, *, with_sessions: bool = False
    ) -> Material | None:
        material = next(
            (item for item in self.materials if item.id == material_id and item.user_id == user_id),
            None,
        )
        if material is not None and with_sessions:
            material.sessions = [
                session for session in self.sessions if session.material_id == material.id
            ]
        return material

    async def get_session(self, user_id: UUID, session_id: UUID) -> LearningSession | None:
        return next(
            (
                session
                for session in self.sessions
                if session.id == session_id and session.user_id == user_id
            ),
            None,
        )

    async def get_active_session(self, user_id: UUID) -> LearningSession | None:
        return next(
            (
                session
                for session in self.sessions
                if session.user_id == user_id
                and session.status == LearningSessionStatus.ACTIVE.value
            ),
            None,
        )

    async def get_note(self, user_id: UUID, note_id: UUID) -> Note | None:
        return next(
            (note for note in self.notes if note.id == note_id and note.user_id == user_id),
            None,
        )

    async def list_material_notes(self, user_id: UUID, material_id: UUID) -> list[Note]:
        return [
            note
            for note in self.notes
            if note.user_id == user_id and note.material_id == material_id
        ]

    def add(self, entity: object) -> None:
        self.pending.append(entity)
        if isinstance(entity, Material):
            entity.created_at = entity.updated_at = datetime.now(UTC)
            entity.sessions = []
            self.materials.append(entity)
        elif isinstance(entity, LearningSession):
            entity.started_at = datetime.now(UTC)
            self.sessions.append(entity)
        elif isinstance(entity, Note):
            entity.created_at = entity.updated_at = datetime.now(UTC)
            self.notes.append(entity)

    async def commit(self) -> None:
        self.committed.append(list(self.pending))
        self.pending.clear()

    async def refresh(self, _entity: object) -> None:
        return None


def make_material(
    repository: FakeMaterialRepository, user_id: UUID = USER_ID, space_id: UUID = SPACE_ID
) -> Material:
    material = Material(
        id=uuid4(),
        user_id=user_id,
        learning_space_id=space_id,
        type="video",
        title="Material",
        status="active",
        material_metadata={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    material.sessions = []
    repository.materials.append(material)
    return material


async def test_cannot_start_session_for_another_users_material() -> None:
    repository = FakeMaterialRepository()
    material = make_material(repository, OTHER_USER_ID)
    service = MaterialService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.start_session(USER_ID, material.id, None)

    assert error.value.code == "material_not_found"


async def test_only_one_active_session_is_allowed() -> None:
    repository = FakeMaterialRepository()
    first_material = make_material(repository)
    second_material = make_material(repository)
    service = MaterialService(repository)  # type: ignore[arg-type]
    await service.start_session(USER_ID, first_material.id, 0)

    with pytest.raises(ApiError) as error:
        await service.start_session(USER_ID, second_material.id, 0)

    assert error.value.code == "active_learning_session_exists"
    assert error.value.status_code == 409


async def test_completing_session_twice_returns_domain_error() -> None:
    repository = FakeMaterialRepository()
    material = make_material(repository)
    service = MaterialService(repository)  # type: ignore[arg-type]
    learning_session = await service.start_session(USER_ID, material.id, 5)
    await service.complete_session(
        USER_ID, learning_session.id, end_position_seconds=30, reflection="Понятно"
    )

    with pytest.raises(ApiError) as error:
        await service.complete_session(
            USER_ID, learning_session.id, end_position_seconds=30, reflection=None
        )

    assert error.value.code == "learning_session_not_active"


async def test_negative_note_timestamp_is_rejected() -> None:
    repository = FakeMaterialRepository()
    service = MaterialService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.create_note(
            USER_ID,
            learning_space_id=SPACE_ID,
            material_id=None,
            learning_session_id=None,
            body="Note",
            source_position_seconds=-1,
            note_type=NoteType.GENERAL,
        )

    assert error.value.code == "negative_source_position"


async def test_note_links_must_share_material_session_and_space() -> None:
    repository = FakeMaterialRepository()
    material = make_material(repository, space_id=SPACE_ID)
    service = MaterialService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.create_note(
            USER_ID,
            learning_space_id=OTHER_SPACE_ID,
            material_id=material.id,
            learning_session_id=None,
            body="Wrong link",
            source_position_seconds=None,
            note_type=NoteType.INSIGHT,
        )

    assert error.value.code == "invalid_note_link"


async def test_outbox_event_is_added_before_material_transaction_commit() -> None:
    repository = FakeMaterialRepository()
    service = MaterialService(repository)  # type: ignore[arg-type]

    material = await service.create_material(
        USER_ID,
        learning_space_id=SPACE_ID,
        type=MaterialType.ARTICLE,
        title="Transactional outbox",
        url=None,
        author=None,
        description=None,
        estimated_minutes=10,
        metadata={},
    )

    transaction = repository.committed[-1]
    assert material in transaction
    event = next(item for item in transaction if isinstance(item, OutboxEvent))
    assert event.event_type == "material.created"
    assert event.aggregate_id == str(material.id)


async def test_api_rejects_negative_timestamp(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/notes",
        json={
            "learning_space_id": str(SPACE_ID),
            "body": "Invalid timestamp",
            "source_position_seconds": -1,
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
