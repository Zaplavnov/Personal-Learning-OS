from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.concepts.domain import ConceptRelationType, ConceptStatus


class ConceptCreate(BaseModel):
    learning_space_id: UUID
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)


class ConceptUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    aliases: list[str] | None = None
    status: ConceptStatus | None = None


class ConceptRelationCreate(BaseModel):
    source_concept_id: UUID
    target_concept_id: UUID
    relation_type: ConceptRelationType
    description: str | None = None


class ConceptRelationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    learning_space_id: UUID
    source_concept_id: UUID
    target_concept_id: UUID
    relation_type: ConceptRelationType
    description: str | None


class ConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    learning_space_id: UUID
    title: str
    description: str | None
    aliases: list[str]
    status: ConceptStatus
    created_at: datetime
    updated_at: datetime


class ConceptDetailResponse(ConceptResponse):
    outgoing_relations: list[ConceptRelationResponse]
    incoming_relations: list[ConceptRelationResponse]


class KnowledgeGraphResponse(BaseModel):
    concepts: list[ConceptResponse]
    relations: list[ConceptRelationResponse]
