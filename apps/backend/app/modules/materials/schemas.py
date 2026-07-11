from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.modules.materials.domain import (
    LearningSessionStatus,
    MaterialStatus,
    MaterialType,
    NoteType,
)


class MaterialCreate(BaseModel):
    learning_space_id: UUID
    type: MaterialType
    title: str = Field(min_length=1, max_length=500)
    url: HttpUrl | None = None
    author: str | None = Field(default=None, max_length=300)
    description: str | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class MaterialUpdate(BaseModel):
    type: MaterialType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=500)
    url: HttpUrl | None = None
    author: str | None = Field(default=None, max_length=300)
    description: str | None = None
    status: MaterialStatus | None = None
    estimated_minutes: int | None = Field(default=None, ge=0)
    metadata: dict[str, Any] | None = None


class LearningSessionStart(BaseModel):
    start_position_seconds: int | None = Field(default=None, ge=0)


class LearningSessionComplete(BaseModel):
    end_position_seconds: int | None = Field(default=None, ge=0)
    reflection: str | None = None


class NoteCreate(BaseModel):
    learning_space_id: UUID
    material_id: UUID | None = None
    learning_session_id: UUID | None = None
    body: str = Field(min_length=1)
    source_position_seconds: int | None = Field(default=None, ge=0)
    note_type: NoteType = NoteType.GENERAL


class NoteUpdate(BaseModel):
    body: str | None = Field(default=None, min_length=1)
    source_position_seconds: int | None = Field(default=None, ge=0)
    note_type: NoteType | None = None


class LearningSessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    material_id: UUID
    user_id: UUID
    started_at: datetime
    ended_at: datetime | None
    start_position_seconds: int | None
    end_position_seconds: int | None
    reflection: str | None
    status: LearningSessionStatus


class MaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    learning_space_id: UUID
    type: MaterialType
    title: str
    url: str | None
    author: str | None
    description: str | None
    status: MaterialStatus
    estimated_minutes: int | None
    metadata: dict[str, Any] = Field(validation_alias="material_metadata")
    created_at: datetime
    updated_at: datetime


class MaterialDetailResponse(MaterialResponse):
    active_session: LearningSessionResponse | None


class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    learning_space_id: UUID
    material_id: UUID | None
    learning_session_id: UUID | None
    body: str
    source_position_seconds: int | None
    note_type: NoteType
    created_at: datetime
    updated_at: datetime
