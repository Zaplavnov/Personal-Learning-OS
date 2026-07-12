from datetime import UTC, datetime, time, timedelta
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.modules.scheduler.domain import (
    CalendarFlexibility,
    CalendarItemStatus,
    build_candidates,
    select_daily_actions,
)
from app.modules.scheduler.infrastructure import (
    CalendarItem,
    ScheduleVersion,
    SqlAlchemySchedulerRepository,
)


class SchedulerService:
    def __init__(self, repository: SqlAlchemySchedulerRepository) -> None:
        self.repository = repository

    async def today(self, user_id: UUID, available_minutes: int, now: datetime | None = None):
        now = now or datetime.now(UTC)
        inputs = await self.repository.load_inputs(user_id, now)
        actions = select_daily_actions(build_candidates(inputs, now), available_minutes)
        return inputs, actions

    async def list_calendar(
        self, user_id: UUID, from_at: datetime, to_at: datetime
    ) -> list[CalendarItem]:
        if to_at <= from_at:
            raise ApiError(
                "invalid_calendar_range", "Calendar range end must be after start", status_code=422
            )
        return await self.repository.list_calendar(user_id, from_at, to_at)

    async def recalculate(
        self,
        user_id: UUID,
        available_minutes: int,
        reason: str,
        now: datetime | None = None,
    ) -> list[CalendarItem]:
        now = now or datetime.now(UTC)
        day_start = datetime.combine(now.date(), time.min, tzinfo=UTC)
        day_end = day_start + timedelta(days=1)
        inputs, actions = await self.today(user_id, available_minutes, now)
        existing = await self.repository.list_flexible_planned(user_id, day_start, day_end)
        by_key = {(item.source_type, item.source_id, item.item_type): item for item in existing}
        selected_keys = {action.key for action in actions}
        for item in existing:
            if (item.source_type, item.source_id, item.item_type) not in selected_keys:
                item.status = CalendarItemStatus.SKIPPED.value

        planned: list[CalendarItem] = []
        cursor = day_start + timedelta(hours=9)
        for action in actions:
            item = by_key.get(action.key)
            if item is None:
                item = CalendarItem(
                    id=uuid4(),
                    user_id=user_id,
                    source_type=action.source_type,
                    source_id=action.source_id,
                    item_type=action.item_type.value,
                    status=CalendarItemStatus.PLANNED.value,
                    flexibility=CalendarFlexibility.FLEXIBLE.value,
                )
                self.repository.add(item)
            item.learning_space_id = action.learning_space_id
            item.title = action.title
            item.planned_start = cursor
            item.estimated_minutes = action.estimated_minutes
            item.priority = action.priority
            item.rationale = action.rationale
            planned.append(item)
            cursor += timedelta(minutes=action.estimated_minutes)
        await self.repository.flush()
        self.repository.add(
            ScheduleVersion(
                id=uuid4(),
                user_id=user_id,
                reason=reason,
                snapshot={
                    "available_minutes": available_minutes,
                    "scheduled_minutes": sum(item.estimated_minutes for item in planned),
                    "items": [
                        {
                            "id": str(item.id),
                            "source_type": item.source_type,
                            "source_id": str(item.source_id) if item.source_id else None,
                            "title": item.title,
                            "estimated_minutes": item.estimated_minutes,
                            "priority": item.priority,
                            "rationale": item.rationale,
                        }
                        for item in planned
                    ],
                    "active_space_id": str(inputs.context.space_id)
                    if inputs.context.space_id
                    else None,
                },
            )
        )
        await self.repository.commit()
        for item in planned:
            await self.repository.refresh(item)
        return planned

    async def update_item(
        self, user_id: UUID, item_id: UUID, changes: dict[str, object]
    ) -> CalendarItem:
        item = await self.repository.get_item(user_id, item_id)
        if item is None:
            raise ApiError(
                "calendar_item_not_found", "Calendar item was not found", status_code=404
            )
        for field, value in changes.items():
            setattr(item, field, value.value if hasattr(value, "value") else value)
        await self.repository.commit()
        await self.repository.refresh(item)
        return item
