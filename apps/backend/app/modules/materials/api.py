from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.modules.materials.application import MaterialService
from app.modules.materials.domain import MaterialType
from app.modules.materials.infrastructure import SqlAlchemyMaterialRepository
from app.modules.materials.schemas import (
    LearningSessionComplete,
    LearningSessionResponse,
    LearningSessionStart,
    MaterialCreate,
    MaterialDetailResponse,
    MaterialResponse,
    MaterialUpdate,
    NoteCreate,
    NoteResponse,
    NoteUpdate,
)

router = APIRouter(tags=["materials"])


def get_material_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> MaterialService:
    return MaterialService(SqlAlchemyMaterialRepository(session))


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Service = Annotated[MaterialService, Depends(get_material_service)]


@router.post("/materials", response_model=MaterialResponse, status_code=status.HTTP_201_CREATED)
async def create_material(
    payload: MaterialCreate, user_id: CurrentUserId, service: Service
) -> MaterialResponse:
    material = await service.create_material(user_id, **payload.model_dump())
    return MaterialResponse.model_validate(material)


@router.get("/materials", response_model=list[MaterialResponse])
async def list_materials(
    user_id: CurrentUserId,
    service: Service,
    learning_space_id: UUID | None = None,
    material_type: Annotated[MaterialType | None, Query(alias="type")] = None,
) -> list[MaterialResponse]:
    materials = await service.list_materials(user_id, learning_space_id, material_type)
    return [MaterialResponse.model_validate(material) for material in materials]


@router.get("/materials/{material_id}", response_model=MaterialDetailResponse)
async def get_material(
    material_id: UUID, user_id: CurrentUserId, service: Service
) -> MaterialDetailResponse:
    return MaterialDetailResponse.model_validate(await service.get_material(user_id, material_id))


@router.patch("/materials/{material_id}", response_model=MaterialResponse)
async def update_material(
    material_id: UUID,
    payload: MaterialUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> MaterialResponse:
    material = await service.update_material(
        user_id, material_id, payload.model_dump(exclude_unset=True)
    )
    return MaterialResponse.model_validate(material)


@router.post(
    "/materials/{material_id}/sessions",
    response_model=LearningSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def start_learning_session(
    material_id: UUID,
    payload: LearningSessionStart,
    user_id: CurrentUserId,
    service: Service,
) -> LearningSessionResponse:
    learning_session = await service.start_session(
        user_id, material_id, payload.start_position_seconds
    )
    return LearningSessionResponse.model_validate(learning_session)


@router.post(
    "/learning-sessions/{session_id}/complete",
    response_model=LearningSessionResponse,
)
async def complete_learning_session(
    session_id: UUID,
    payload: LearningSessionComplete,
    user_id: CurrentUserId,
    service: Service,
) -> LearningSessionResponse:
    learning_session = await service.complete_session(user_id, session_id, **payload.model_dump())
    return LearningSessionResponse.model_validate(learning_session)


@router.post("/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    payload: NoteCreate, user_id: CurrentUserId, service: Service
) -> NoteResponse:
    note = await service.create_note(user_id, **payload.model_dump())
    return NoteResponse.model_validate(note)


@router.patch("/notes/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: UUID, payload: NoteUpdate, user_id: CurrentUserId, service: Service
) -> NoteResponse:
    note = await service.update_note(user_id, note_id, payload.model_dump(exclude_unset=True))
    return NoteResponse.model_validate(note)


@router.get("/materials/{material_id}/notes", response_model=list[NoteResponse])
async def list_material_notes(
    material_id: UUID, user_id: CurrentUserId, service: Service
) -> list[NoteResponse]:
    notes = await service.list_material_notes(user_id, material_id)
    return [NoteResponse.model_validate(note) for note in notes]
