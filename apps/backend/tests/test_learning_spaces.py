from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.errors import ApiError
from app.modules.learning_spaces.api import get_learning_space_service
from app.modules.learning_spaces.application import LearningSpaceService
from app.modules.learning_spaces.domain import LearningGoalStatus
from app.modules.learning_spaces.infrastructure import LearningGoal, LearningSpace

LOCAL_USER_ID = UUID("00000000-0000-4000-8000-000000000001")
OTHER_USER_ID = uuid4()


def test_learning_space_user_foreign_key_is_resolvable() -> None:
    foreign_key = next(iter(LearningSpace.__table__.foreign_keys))

    assert foreign_key.column.table.name == "users"


class FakeRepository:
    def __init__(self) -> None:
        self.spaces: list[LearningSpace] = []
        self.goals: list[LearningGoal] = []

    async def list_spaces(self, user_id: UUID) -> list[LearningSpace]:
        return [space for space in self.spaces if space.user_id == user_id]

    async def get_space(self, user_id: UUID, space_id: UUID) -> LearningSpace | None:
        return next(
            (space for space in self.spaces if space.id == space_id and space.user_id == user_id),
            None,
        )

    async def lock_space(self, user_id: UUID, space_id: UUID) -> LearningSpace | None:
        return await self.get_space(user_id, space_id)

    async def get_goal(self, user_id: UUID, goal_id: UUID) -> LearningGoal | None:
        goal = next((item for item in self.goals if item.id == goal_id), None)
        if goal is None:
            return None
        space = await self.get_space(user_id, goal.learning_space_id)
        return goal if space is not None else None

    async def pause_active_goals(self, space_id: UUID, except_goal_id: UUID | None = None) -> None:
        for goal in self.goals:
            if (
                goal.learning_space_id == space_id
                and goal.status == LearningGoalStatus.ACTIVE.value
                and goal.id != except_goal_id
            ):
                goal.status = LearningGoalStatus.PAUSED.value

    def add_space(self, space: LearningSpace) -> None:
        space.id = space.id or uuid4()
        space.created_at = space.updated_at = datetime.now(UTC)
        space.goals = []
        self.spaces.append(space)

    def add_goal(self, goal: LearningGoal) -> None:
        goal.id = goal.id or uuid4()
        goal.created_at = goal.updated_at = datetime.now(UTC)
        self.goals.append(goal)

    async def commit(self) -> None:
        return None

    async def refresh_space(self, space: LearningSpace) -> LearningSpace:
        space.goals = [goal for goal in self.goals if goal.learning_space_id == space.id]
        return space

    async def refresh_goal(self, _user_id: UUID, goal: LearningGoal) -> LearningGoal:
        return goal


def make_space(repository: FakeRepository, user_id: UUID = LOCAL_USER_ID) -> LearningSpace:
    space = LearningSpace(
        id=uuid4(),
        user_id=user_id,
        title="Space",
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.spaces.append(space)
    return space


def make_goal(
    repository: FakeRepository, space: LearningSpace, status: LearningGoalStatus
) -> LearningGoal:
    goal = LearningGoal(
        id=uuid4(),
        learning_space_id=space.id,
        title=f"Goal {len(repository.goals) + 1}",
        priority=0,
        status=status.value,
        expected_capabilities=[],
        completion_criteria=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    repository.goals.append(goal)
    return goal


async def test_activating_goal_pauses_previous_active_goal() -> None:
    repository = FakeRepository()
    space = make_space(repository)
    previous = make_goal(repository, space, LearningGoalStatus.ACTIVE)
    next_goal = make_goal(repository, space, LearningGoalStatus.PAUSED)
    service = LearningSpaceService(repository)  # type: ignore[arg-type]

    activated = await service.activate_goal(LOCAL_USER_ID, next_goal.id)

    assert activated.status == LearningGoalStatus.ACTIVE.value
    assert previous.status == LearningGoalStatus.PAUSED.value


async def test_creating_active_goal_pauses_previous_goal() -> None:
    repository = FakeRepository()
    space = make_space(repository)
    previous = make_goal(repository, space, LearningGoalStatus.ACTIVE)
    service = LearningSpaceService(repository)  # type: ignore[arg-type]

    created = await service.create_goal(
        LOCAL_USER_ID,
        space.id,
        title="New active goal",
        description=None,
        priority=10,
        status=LearningGoalStatus.ACTIVE,
        target_date=None,
        expected_capabilities=[],
        completion_criteria=[],
    )

    assert created.status == LearningGoalStatus.ACTIVE.value
    assert previous.status == LearningGoalStatus.PAUSED.value


async def test_user_cannot_access_another_users_space() -> None:
    repository = FakeRepository()
    other_space = make_space(repository, OTHER_USER_ID)
    service = LearningSpaceService(repository)  # type: ignore[arg-type]

    with pytest.raises(ApiError) as error:
        await service.get_space(LOCAL_USER_ID, other_space.id)

    assert error.value.status_code == 404
    assert error.value.code == "learning_space_not_found"


async def test_learning_spaces_api_uses_current_user(app: FastAPI) -> None:
    now = datetime.now(UTC)
    response_space = SimpleNamespace(
        id=uuid4(),
        user_id=LOCAL_USER_ID,
        title="API space",
        description=None,
        color=None,
        status="active",
        created_at=now,
        updated_at=now,
        goals=[],
    )

    class StubService:
        async def list_spaces(self, user_id: UUID):
            assert user_id == LOCAL_USER_ID
            return [response_space]

    app.dependency_overrides[get_learning_space_service] = lambda: StubService()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/learning-spaces")

    assert response.status_code == 200
    assert response.json()[0]["title"] == "API space"
