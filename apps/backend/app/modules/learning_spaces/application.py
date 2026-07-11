from datetime import date
from uuid import UUID

from app.core.errors import ApiError
from app.modules.learning_spaces.domain import LearningGoalStatus, LearningSpaceStatus
from app.modules.learning_spaces.infrastructure import (
    LearningGoal,
    LearningSpace,
    SqlAlchemyLearningSpaceRepository,
)


class LearningSpaceService:
    def __init__(self, repository: SqlAlchemyLearningSpaceRepository) -> None:
        self.repository = repository

    async def create_space(
        self,
        user_id: UUID,
        *,
        title: str,
        description: str | None,
        color: str | None,
    ) -> LearningSpace:
        space = LearningSpace(
            user_id=user_id,
            title=title,
            description=description,
            color=color,
            status=LearningSpaceStatus.ACTIVE.value,
        )
        self.repository.add_space(space)
        await self.repository.commit()
        return await self.repository.refresh_space(space)

    async def list_spaces(self, user_id: UUID) -> list[LearningSpace]:
        return await self.repository.list_spaces(user_id)

    async def get_space(self, user_id: UUID, space_id: UUID) -> LearningSpace:
        space = await self.repository.get_space(user_id, space_id)
        if space is None:
            raise self._space_not_found()
        return space

    async def update_space(
        self, user_id: UUID, space_id: UUID, changes: dict[str, object]
    ) -> LearningSpace:
        space = await self.get_space(user_id, space_id)
        for field, value in changes.items():
            if field == "status" and isinstance(value, LearningSpaceStatus):
                value = value.value
            setattr(space, field, value)
        await self.repository.commit()
        return await self.repository.refresh_space(space)

    async def create_goal(
        self,
        user_id: UUID,
        space_id: UUID,
        *,
        title: str,
        description: str | None,
        priority: int,
        status: LearningGoalStatus,
        target_date: date | None,
        expected_capabilities: list[str],
        completion_criteria: list[str],
    ) -> LearningGoal:
        space = await self.repository.lock_space(user_id, space_id)
        if space is None:
            raise self._space_not_found()
        if status is LearningGoalStatus.ACTIVE:
            await self.repository.pause_active_goals(space_id)
        goal = LearningGoal(
            learning_space_id=space_id,
            title=title,
            description=description,
            priority=priority,
            status=status.value,
            target_date=target_date,
            expected_capabilities=expected_capabilities,
            completion_criteria=completion_criteria,
        )
        self.repository.add_goal(goal)
        await self.repository.commit()
        return await self.repository.refresh_goal(user_id, goal)

    async def update_goal(
        self, user_id: UUID, goal_id: UUID, changes: dict[str, object]
    ) -> LearningGoal:
        goal = await self.repository.get_goal(user_id, goal_id)
        if goal is None:
            raise self._goal_not_found()

        requested_status = changes.pop("status", None)
        if requested_status == LearningGoalStatus.ACTIVE:
            space = await self.repository.lock_space(user_id, goal.learning_space_id)
            if space is None:
                raise self._space_not_found()
            await self.repository.pause_active_goals(goal.learning_space_id, goal.id)
            goal.status = LearningGoalStatus.ACTIVE.value
        elif isinstance(requested_status, LearningGoalStatus):
            goal.status = requested_status.value

        for field, value in changes.items():
            setattr(goal, field, value)
        await self.repository.commit()
        return await self.repository.refresh_goal(user_id, goal)

    async def activate_goal(self, user_id: UUID, goal_id: UUID) -> LearningGoal:
        goal = await self.repository.get_goal(user_id, goal_id)
        if goal is None:
            raise self._goal_not_found()
        space = await self.repository.lock_space(user_id, goal.learning_space_id)
        if space is None:
            raise self._space_not_found()
        await self.repository.pause_active_goals(goal.learning_space_id, goal.id)
        goal.status = LearningGoalStatus.ACTIVE.value
        await self.repository.commit()
        return await self.repository.refresh_goal(user_id, goal)

    @staticmethod
    def _space_not_found() -> ApiError:
        return ApiError(
            code="learning_space_not_found",
            message="Learning space was not found",
            status_code=404,
        )

    @staticmethod
    def _goal_not_found() -> ApiError:
        return ApiError(
            code="learning_goal_not_found",
            message="Learning goal was not found",
            status_code=404,
        )
