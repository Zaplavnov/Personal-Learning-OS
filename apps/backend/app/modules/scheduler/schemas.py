from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.scheduler.domain import CalendarFlexibility, CalendarItemStatus, CalendarItemType


class ActiveSpaceSummary(BaseModel):
    id: UUID
    title: str


class ActiveGoalSummary(BaseModel):
    id: UUID
    title: str


class TodayAction(BaseModel):
    item_type: CalendarItemType
    source_type: str
    source_id: UUID | None
    learning_space_id: UUID | None
    title: str
    estimated_minutes: int
    priority: int
    rationale: str
    action_url: str
    target_dimension: str


class KnowledgeStabilitySummary(BaseModel):
    average: float
    confidence: float
    concept_count: int


class TodayResponse(BaseModel):
    available_minutes: int
    scheduled_minutes: int
    active_space: ActiveSpaceSummary | None
    active_goal: ActiveGoalSummary | None
    primary_action: TodayAction | None
    secondary_actions: list[TodayAction]
    due_review_count: int
    open_gap_count: int
    knowledge_stability: KnowledgeStabilitySummary
    next_item: TodayAction | None


class CalendarItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    learning_space_id: UUID | None
    item_type: CalendarItemType
    source_type: str
    source_id: UUID | None
    title: str
    planned_start: datetime | None
    estimated_minutes: int
    status: CalendarItemStatus
    flexibility: CalendarFlexibility
    priority: int
    rationale: str
    created_at: datetime
    updated_at: datetime


class RecalculateSchedule(BaseModel):
    available_minutes: int = Field(default=45, ge=15, le=180)
    reason: str = Field(default="manual_recalculation", min_length=1, max_length=200)


class CalendarItemUpdate(BaseModel):
    planned_start: datetime | None = None
    estimated_minutes: int | None = Field(default=None, gt=0, le=480)
    status: CalendarItemStatus | None = None
    flexibility: CalendarFlexibility | None = None
    priority: int | None = None
