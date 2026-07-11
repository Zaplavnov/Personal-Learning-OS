from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.modules.learning_spaces.application import LearningSpaceService
from app.modules.learning_spaces.infrastructure import SqlAlchemyLearningSpaceRepository
from app.modules.learning_spaces.schemas import (
    LearningGoalCreate,
    LearningGoalResponse,
    LearningGoalUpdate,
    LearningSpaceCreate,
    LearningSpaceResponse,
    LearningSpaceUpdate,
)

router = APIRouter(tags=["learning-spaces"])


def get_learning_space_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LearningSpaceService:
    return LearningSpaceService(SqlAlchemyLearningSpaceRepository(session))


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Service = Annotated[LearningSpaceService, Depends(get_learning_space_service)]


@router.post(
    "/learning-spaces",
    response_model=LearningSpaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_learning_space(
    payload: LearningSpaceCreate, user_id: CurrentUserId, service: Service
) -> LearningSpaceResponse:
    space = await service.create_space(user_id, **payload.model_dump())
    return LearningSpaceResponse.model_validate(space)


@router.get("/learning-spaces", response_model=list[LearningSpaceResponse])
async def list_learning_spaces(
    user_id: CurrentUserId, service: Service
) -> list[LearningSpaceResponse]:
    spaces = await service.list_spaces(user_id)
    return [LearningSpaceResponse.model_validate(space) for space in spaces]


@router.get("/learning-spaces/{space_id}", response_model=LearningSpaceResponse)
async def get_learning_space(
    space_id: UUID, user_id: CurrentUserId, service: Service
) -> LearningSpaceResponse:
    space = await service.get_space(user_id, space_id)
    return LearningSpaceResponse.model_validate(space)


@router.patch("/learning-spaces/{space_id}", response_model=LearningSpaceResponse)
async def update_learning_space(
    space_id: UUID,
    payload: LearningSpaceUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> LearningSpaceResponse:
    space = await service.update_space(user_id, space_id, payload.model_dump(exclude_unset=True))
    return LearningSpaceResponse.model_validate(space)


@router.post(
    "/learning-spaces/{space_id}/goals",
    response_model=LearningGoalResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_learning_goal(
    space_id: UUID,
    payload: LearningGoalCreate,
    user_id: CurrentUserId,
    service: Service,
) -> LearningGoalResponse:
    goal = await service.create_goal(user_id, space_id, **payload.model_dump())
    return LearningGoalResponse.model_validate(goal)


@router.patch("/learning-goals/{goal_id}", response_model=LearningGoalResponse)
async def update_learning_goal(
    goal_id: UUID,
    payload: LearningGoalUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> LearningGoalResponse:
    goal = await service.update_goal(user_id, goal_id, payload.model_dump(exclude_unset=True))
    return LearningGoalResponse.model_validate(goal)


@router.post("/learning-goals/{goal_id}/activate", response_model=LearningGoalResponse)
async def activate_learning_goal(
    goal_id: UUID, user_id: CurrentUserId, service: Service
) -> LearningGoalResponse:
    goal = await service.activate_goal(user_id, goal_id)
    return LearningGoalResponse.model_validate(goal)
