from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.learning_spaces.domain import LearningGoalStatus, LearningSpaceStatus


class LearningSpaceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, max_length=32)


class LearningSpaceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    color: str | None = Field(default=None, max_length=32)
    status: LearningSpaceStatus | None = None


class LearningGoalCreate(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    priority: int = Field(default=0, ge=0)
    status: LearningGoalStatus = LearningGoalStatus.PAUSED
    target_date: date | None = None
    expected_capabilities: list[str] = Field(default_factory=list)
    completion_criteria: list[str] = Field(default_factory=list)


class LearningGoalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    priority: int | None = Field(default=None, ge=0)
    status: LearningGoalStatus | None = None
    target_date: date | None = None
    expected_capabilities: list[str] | None = None
    completion_criteria: list[str] | None = None


class LearningGoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    learning_space_id: UUID
    title: str
    description: str | None
    priority: int
    status: LearningGoalStatus
    target_date: date | None
    expected_capabilities: list[str]
    completion_criteria: list[str]
    created_at: datetime
    updated_at: datetime


class LearningSpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    description: str | None
    color: str | None
    status: LearningSpaceStatus
    created_at: datetime
    updated_at: datetime
    goals: list[LearningGoalResponse]
