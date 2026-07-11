from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.modules.materials.domain import (
    LearningSessionStatus,
    MaterialStatus,
    MaterialType,
    NoteType,
)
from app.modules.materials.infrastructure import (
    LearningSession,
    Material,
    Note,
    SqlAlchemyMaterialRepository,
)
from app.modules.outbox.models import OutboxEvent


class MaterialService:
    def __init__(self, repository: SqlAlchemyMaterialRepository) -> None:
        self.repository = repository

    async def create_material(
        self,
        user_id: UUID,
        *,
        learning_space_id: UUID,
        type: MaterialType,
        title: str,
        url: str | None,
        author: str | None,
        description: str | None,
        estimated_minutes: int | None,
        metadata: dict[str, object],
    ) -> Material:
        if not await self.repository.owns_space(user_id, learning_space_id):
            raise self._space_not_found()
        material = Material(
            id=uuid4(),
            user_id=user_id,
            learning_space_id=learning_space_id,
            type=type.value,
            title=title,
            url=str(url) if url is not None else None,
            author=author,
            description=description,
            status=MaterialStatus.ACTIVE.value,
            estimated_minutes=estimated_minutes,
            material_metadata=metadata,
        )
        self.repository.add(material)
        self.repository.add(
            self._event("material.created", "material", material.id, user_id, learning_space_id)
        )
        await self.repository.commit()
        await self.repository.refresh(material)
        return material

    async def list_materials(
        self, user_id: UUID, space_id: UUID | None, material_type: MaterialType | None
    ) -> list[Material]:
        return await self.repository.list_materials(
            user_id, space_id, material_type.value if material_type else None
        )

    async def get_material(self, user_id: UUID, material_id: UUID) -> Material:
        material = await self.repository.get_material(user_id, material_id, with_sessions=True)
        if material is None:
            raise self._material_not_found()
        return material

    async def update_material(
        self, user_id: UUID, material_id: UUID, changes: dict[str, object]
    ) -> Material:
        material = await self.repository.get_material(user_id, material_id)
        if material is None:
            raise self._material_not_found()
        for field, value in changes.items():
            if field == "type" and isinstance(value, MaterialType):
                value = value.value
            elif field == "status" and isinstance(value, MaterialStatus):
                value = value.value
            elif field == "metadata":
                field = "material_metadata"
            setattr(material, field, value)
        await self.repository.commit()
        await self.repository.refresh(material)
        return material

    async def start_session(
        self, user_id: UUID, material_id: UUID, start_position_seconds: int | None
    ) -> LearningSession:
        self._validate_position(start_position_seconds)
        await self.repository.lock_user(user_id)
        material = await self.repository.get_material(user_id, material_id)
        if material is None:
            raise self._material_not_found()
        if await self.repository.get_active_session(user_id) is not None:
            raise ApiError(
                code="active_learning_session_exists",
                message="Complete the active learning session before starting another one",
                status_code=409,
            )
        learning_session = LearningSession(
            id=uuid4(),
            material_id=material.id,
            user_id=user_id,
            start_position_seconds=start_position_seconds,
            status=LearningSessionStatus.ACTIVE.value,
        )
        self.repository.add(learning_session)
        self.repository.add(
            self._event(
                "learning_session.started",
                "learning_session",
                learning_session.id,
                user_id,
                material.learning_space_id,
                {"material_id": str(material.id)},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(learning_session)
        return learning_session

    async def complete_session(
        self,
        user_id: UUID,
        session_id: UUID,
        *,
        end_position_seconds: int | None,
        reflection: str | None,
    ) -> LearningSession:
        self._validate_position(end_position_seconds)
        learning_session = await self.repository.get_session(user_id, session_id)
        if learning_session is None:
            raise self._session_not_found()
        if learning_session.status != LearningSessionStatus.ACTIVE.value:
            raise ApiError(
                code="learning_session_not_active",
                message="Learning session is already finished",
                status_code=409,
            )
        learning_session.status = LearningSessionStatus.COMPLETED.value
        learning_session.ended_at = datetime.now(UTC)
        learning_session.end_position_seconds = end_position_seconds
        learning_session.reflection = reflection
        material = await self.repository.get_material(user_id, learning_session.material_id)
        if material is None:
            raise self._material_not_found()
        self.repository.add(
            self._event(
                "learning_activity.completed",
                "learning_session",
                learning_session.id,
                user_id,
                material.learning_space_id,
                {"material_id": str(material.id)},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(learning_session)
        return learning_session

    async def create_note(
        self,
        user_id: UUID,
        *,
        learning_space_id: UUID,
        material_id: UUID | None,
        learning_session_id: UUID | None,
        body: str,
        source_position_seconds: int | None,
        note_type: NoteType,
    ) -> Note:
        self._validate_position(source_position_seconds)
        if not await self.repository.owns_space(user_id, learning_space_id):
            raise self._space_not_found()

        material = None
        if material_id is not None:
            material = await self.repository.get_material(user_id, material_id)
            if material is None:
                raise self._material_not_found()
            if material.learning_space_id != learning_space_id:
                raise self._invalid_note_link()

        if learning_session_id is not None:
            learning_session = await self.repository.get_session(user_id, learning_session_id)
            if learning_session is None:
                raise self._session_not_found()
            if material is None:
                material = await self.repository.get_material(user_id, learning_session.material_id)
                material_id = learning_session.material_id
            if material is None or learning_session.material_id != material.id:
                raise self._invalid_note_link()
            if material.learning_space_id != learning_space_id:
                raise self._invalid_note_link()

        note = Note(
            id=uuid4(),
            user_id=user_id,
            learning_space_id=learning_space_id,
            material_id=material_id,
            learning_session_id=learning_session_id,
            body=body,
            source_position_seconds=source_position_seconds,
            note_type=note_type.value,
        )
        self.repository.add(note)
        self.repository.add(
            self._event(
                "note.created",
                "note",
                note.id,
                user_id,
                learning_space_id,
                {"material_id": str(material_id) if material_id else None},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(note)
        return note

    async def update_note(self, user_id: UUID, note_id: UUID, changes: dict[str, object]) -> Note:
        note = await self.repository.get_note(user_id, note_id)
        if note is None:
            raise self._note_not_found()
        if "source_position_seconds" in changes:
            self._validate_position(changes["source_position_seconds"])
        for field, value in changes.items():
            if field == "note_type" and isinstance(value, NoteType):
                value = value.value
            setattr(note, field, value)
        await self.repository.commit()
        await self.repository.refresh(note)
        return note

    async def list_material_notes(self, user_id: UUID, material_id: UUID) -> list[Note]:
        if await self.repository.get_material(user_id, material_id) is None:
            raise self._material_not_found()
        return await self.repository.list_material_notes(user_id, material_id)

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
    def _validate_position(value: object) -> None:
        if isinstance(value, int) and value < 0:
            raise ApiError(
                code="negative_source_position",
                message="Source position cannot be negative",
                status_code=422,
            )

    @staticmethod
    def _material_not_found() -> ApiError:
        return ApiError("material_not_found", "Material was not found", status_code=404)

    @staticmethod
    def _space_not_found() -> ApiError:
        return ApiError("learning_space_not_found", "Learning space was not found", status_code=404)

    @staticmethod
    def _session_not_found() -> ApiError:
        return ApiError(
            "learning_session_not_found", "Learning session was not found", status_code=404
        )

    @staticmethod
    def _note_not_found() -> ApiError:
        return ApiError("note_not_found", "Note was not found", status_code=404)

    @staticmethod
    def _invalid_note_link() -> ApiError:
        return ApiError(
            "invalid_note_link",
            "Note links must belong to the same user, material, and learning space",
            status_code=422,
        )
