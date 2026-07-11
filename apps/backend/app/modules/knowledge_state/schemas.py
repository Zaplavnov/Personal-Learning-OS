from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.knowledge_state.domain import (
    EvidenceType,
    KnowledgeDimension,
    ReviewResult,
    ReviewStatus,
    ReviewType,
)


class EvidenceCreate(BaseModel):
    evidence_type: EvidenceType
    dimension: KnowledgeDimension
    score_delta: float = Field(ge=-100, le=100)
    strength: float | None = Field(default=None, ge=0, le=1)
    source_type: str = Field(default="manual", min_length=1, max_length=60)
    source_id: str | None = Field(default=None, max_length=100)
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    concept_id: UUID
    evidence_type: EvidenceType
    dimension: KnowledgeDimension
    score_delta: float
    strength: float
    source_type: str
    source_id: str | None
    metadata: dict[str, Any] = Field(validation_alias="evidence_metadata")
    occurred_at: datetime


class ConceptStateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept_id: UUID
    recall: float
    explanation: float
    structure: float
    comparison: float
    application: float
    hypothesis_generation: float
    stability: float
    confidence: float
    last_evidence_at: datetime | None
    next_review_at: datetime | None
    version: int
    updated_at: datetime


class ConceptStateDetailResponse(ConceptStateResponse):
    evidence_count: int
    recent_evidence: list[EvidenceResponse]


class EvidenceCreatedResponse(BaseModel):
    evidence: EvidenceResponse
    state: ConceptStateResponse


class ReviewItemCreate(BaseModel):
    concept_id: UUID
    review_type: ReviewType
    prompt: str = Field(min_length=1)
    expected_points: list[str] = Field(default_factory=list)
    due_at: datetime | None = None


class ReviewItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    concept_id: UUID
    review_type: ReviewType
    prompt: str
    expected_points: list[str]
    status: ReviewStatus
    due_at: datetime
    created_at: datetime


class ReviewAttemptCreate(BaseModel):
    answer: str = Field(min_length=1)
    self_rating: int = Field(ge=1, le=5)
    result: ReviewResult
    feedback: str | None = None


class ReviewAttemptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    review_item_id: UUID
    answer: str
    self_rating: int
    result: ReviewResult
    feedback: str | None
    created_at: datetime


class ReviewSubmittedResponse(BaseModel):
    attempt: ReviewAttemptResponse
    state: ConceptStateResponse
    next_review: ReviewItemResponse


class ReviewReschedule(BaseModel):
    due_at: datetime
