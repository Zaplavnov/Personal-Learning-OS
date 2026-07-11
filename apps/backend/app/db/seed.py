import asyncio
import logging
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert

from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.db.session import async_session_factory
from app.modules.users.models import User

logger = logging.getLogger(__name__)


def build_local_user_statement(settings: Settings):
    statement = insert(User).values(
        id=UUID(settings.local_user_id),
        email=settings.local_user_email,
        display_name=settings.local_user_display_name,
        timezone=settings.local_user_timezone,
        is_active=True,
    )
    statement = statement.on_conflict_do_update(
        index_elements=[User.email],
        set_={
            "display_name": statement.excluded.display_name,
            "timezone": statement.excluded.timezone,
            "is_active": True,
        },
    )
    return statement


async def seed_local_user() -> None:
    settings = get_settings()
    statement = build_local_user_statement(settings)
    async with async_session_factory() as session:
        await session.execute(statement)
        await session.commit()
    logger.info("local_user_seeded", extra={"user_id": settings.local_user_id})


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    await seed_local_user()


if __name__ == "__main__":
    asyncio.run(main())
