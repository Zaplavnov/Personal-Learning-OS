import asyncio
import logging
from uuid import UUID

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.seed import seed_local_user
from app.db.session import async_session_factory
from app.modules.learning_spaces.domain import LearningGoalStatus, LearningSpaceStatus
from app.modules.learning_spaces.infrastructure import LearningGoal, LearningSpace

logger = logging.getLogger(__name__)

SPACE_ID = UUID("10000000-0000-4000-8000-000000000001")
GOAL_ID = UUID("20000000-0000-4000-8000-000000000001")


async def seed_learning_spaces() -> None:
    settings = get_settings()
    await seed_local_user()

    space_statement = insert(LearningSpace).values(
        id=SPACE_ID,
        user_id=UUID(settings.local_user_id),
        title="Линейная алгебра",
        description="Геометрическая интуиция, формальные основы и применение в ML.",
        color="#5f7894",
        status=LearningSpaceStatus.ACTIVE.value,
    )
    space_statement = space_statement.on_conflict_do_update(
        index_elements=[LearningSpace.id],
        set_={
            "title": space_statement.excluded.title,
            "description": space_statement.excluded.description,
            "color": space_statement.excluded.color,
            "status": space_statement.excluded.status,
        },
    )

    goal_statement = insert(LearningGoal).values(
        id=GOAL_ID,
        learning_space_id=SPACE_ID,
        title="Понять геометрический смысл линейных преобразований",
        description="Объединить формальные определения и визуальную интуицию.",
        priority=100,
        status=LearningGoalStatus.ACTIVE.value,
        expected_capabilities=[
            "Объяснять линейные преобразования геометрически",
            "Распознавать их применение в задачах",
        ],
        completion_criteria=[
            "Самостоятельно объяснить действие матрицы",
            "Решить практическую задачу без подсказки",
        ],
    )
    goal_statement = goal_statement.on_conflict_do_update(
        index_elements=[LearningGoal.id],
        set_={
            "title": goal_statement.excluded.title,
            "description": goal_statement.excluded.description,
            "priority": goal_statement.excluded.priority,
            "status": goal_statement.excluded.status,
            "expected_capabilities": goal_statement.excluded.expected_capabilities,
            "completion_criteria": goal_statement.excluded.completion_criteria,
        },
    )

    async with async_session_factory() as session:
        await session.execute(space_statement)
        await session.execute(
            update(LearningGoal)
            .where(
                LearningGoal.learning_space_id == SPACE_ID,
                LearningGoal.status == LearningGoalStatus.ACTIVE.value,
                LearningGoal.id != GOAL_ID,
            )
            .values(status=LearningGoalStatus.PAUSED.value)
        )
        await session.execute(goal_statement)
        await session.commit()
    logger.info("learning_spaces_seeded", extra={"space_id": str(SPACE_ID)})


async def main() -> None:
    configure_logging(get_settings().log_level)
    await seed_learning_spaces()


if __name__ == "__main__":
    asyncio.run(main())
