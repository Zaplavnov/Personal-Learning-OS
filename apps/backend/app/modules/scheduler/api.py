from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.modules.scheduler.application import SchedulerService
from app.modules.scheduler.infrastructure import SqlAlchemySchedulerRepository
from app.modules.scheduler.schemas import (
    ActiveGoalSummary,
    ActiveSpaceSummary,
    CalendarItemResponse,
    CalendarItemUpdate,
    KnowledgeStabilitySummary,
    RecalculateSchedule,
    TodayAction,
    TodayResponse,
)

router = APIRouter(tags=["scheduler", "calendar"])


def get_scheduler_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SchedulerService:
    return SchedulerService(SqlAlchemySchedulerRepository(session))


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Service = Annotated[SchedulerService, Depends(get_scheduler_service)]


@router.get("/today", response_model=TodayResponse)
async def get_today(
    user_id: CurrentUserId,
    service: Service,
    available_minutes: Annotated[int, Query(ge=15, le=180)] = 45,
) -> TodayResponse:
    inputs, actions = await service.today(user_id, available_minutes)
    serialized = [TodayAction.model_validate(action, from_attributes=True) for action in actions]
    return TodayResponse(
        available_minutes=available_minutes,
        scheduled_minutes=sum(action.estimated_minutes for action in actions),
        active_space=(
            ActiveSpaceSummary(id=inputs.context.space_id, title=inputs.context.space_title)
            if inputs.context.space_id and inputs.context.space_title
            else None
        ),
        active_goal=(
            ActiveGoalSummary(id=inputs.context.goal_id, title=inputs.context.goal_title)
            if inputs.context.goal_id and inputs.context.goal_title
            else None
        ),
        primary_action=serialized[0] if serialized else None,
        secondary_actions=serialized[1:],
        due_review_count=len(inputs.due_reviews),
        open_gap_count=len(inputs.open_gaps),
        knowledge_stability=KnowledgeStabilitySummary(
            average=round(inputs.average_stability, 2),
            confidence=round(inputs.average_confidence, 4),
            concept_count=inputs.state_count,
        ),
        next_item=serialized[1] if len(serialized) > 1 else None,
    )


@router.get("/calendar", response_model=list[CalendarItemResponse])
async def get_calendar(
    user_id: CurrentUserId,
    service: Service,
    from_at: Annotated[datetime | None, Query(alias="from")] = None,
    to_at: Annotated[datetime | None, Query(alias="to")] = None,
) -> list[CalendarItemResponse]:
    now = datetime.now(UTC)
    start = from_at or now - timedelta(days=7)
    end = to_at or now + timedelta(days=30)
    return [
        CalendarItemResponse.model_validate(item)
        for item in await service.list_calendar(user_id, start, end)
    ]


@router.post("/calendar/recalculate", response_model=list[CalendarItemResponse])
async def recalculate_calendar(
    payload: RecalculateSchedule, user_id: CurrentUserId, service: Service
) -> list[CalendarItemResponse]:
    items = await service.recalculate(user_id, payload.available_minutes, payload.reason)
    return [CalendarItemResponse.model_validate(item) for item in items]


@router.patch("/calendar-items/{item_id}", response_model=CalendarItemResponse)
async def update_calendar_item(
    item_id: UUID,
    payload: CalendarItemUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> CalendarItemResponse:
    item = await service.update_item(user_id, item_id, payload.model_dump(exclude_unset=True))
    return CalendarItemResponse.model_validate(item)
