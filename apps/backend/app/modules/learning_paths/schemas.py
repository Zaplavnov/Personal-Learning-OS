from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.modules.learning_paths.domain import (
    EdgeType,
    NodeImportance,
    NodeStatus,
    NodeType,
    PathStatus,
    ResourceStatus,
    ResourceType,
    SuggestionSource,
    SuggestionStatus,
    SuggestionType,
)


class GenerateDraftRequest(BaseModel):
    target_concept_ids: list[UUID] = Field(min_length=1)
    max_depth: int = Field(default=4, ge=1, le=10)
    title: str | None = Field(default=None, max_length=300)


class LearningPathCreate(BaseModel):
    learning_goal_id: UUID
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None


class LearningPathUpdate(BaseModel):
    expected_version: int = Field(ge=0)
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    status: PathStatus | None = None


class VersionedMutation(BaseModel):
    expected_version: int = Field(ge=0)


class NodeCreate(VersionedMutation):
    concept_id: UUID | None = None
    node_type: NodeType
    title: str = Field(min_length=1, max_length=300)
    description: str | None = None
    position_x: float | None = None
    position_y: float | None = None
    status: NodeStatus = NodeStatus.PLANNED
    importance: NodeImportance = NodeImportance.REQUIRED
    estimated_minutes: int | None = Field(default=None, gt=0)
    completion_policy: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class NodeUpdate(VersionedMutation):
    concept_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    position_x: float | None = None
    position_y: float | None = None
    status: NodeStatus | None = None
    importance: NodeImportance | None = None
    estimated_minutes: int | None = Field(default=None, gt=0)
    completion_policy: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


class EdgeCreate(VersionedMutation):
    source_node_id: UUID
    target_node_id: UUID
    edge_type: EdgeType
    condition: dict[str, Any] | None = None
    label: str | None = Field(default=None, max_length=200)


class EdgeUpdate(VersionedMutation):
    edge_type: EdgeType | None = None
    condition: dict[str, Any] | None = None
    label: str | None = Field(default=None, max_length=200)


class ResourceCreate(VersionedMutation):
    resource_type: ResourceType
    resource_id: UUID | None = None
    title: str = Field(min_length=1, max_length=500)
    is_required: bool = False
    order_index: int = Field(default=0, ge=0)
    completion_status: ResourceStatus = ResourceStatus.PLANNED
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResourceUpdate(VersionedMutation):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    is_required: bool | None = None
    order_index: int | None = Field(default=None, ge=0)
    completion_status: ResourceStatus | None = None
    metadata: dict[str, Any] | None = None


class SuggestionCreate(BaseModel):
    expected_version: int = Field(ge=0)
    suggestion_type: SuggestionType
    payload: dict[str, Any]
    rationale: str = Field(min_length=1)
    source: SuggestionSource = SuggestionSource.USER


class RestoreVersionRequest(VersionedMutation):
    change_summary: str = Field(default="Restored previous path version", max_length=500)


class LearningPathResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    learning_space_id: UUID
    learning_goal_id: UUID
    title: str
    description: str | None
    status: PathStatus
    current_node_id: UUID | None
    version: int
    created_at: datetime
    updated_at: datetime


class NodeResourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    node_id: UUID
    resource_type: ResourceType
    resource_id: UUID | None
    title: str
    is_required: bool
    order_index: int
    completion_status: ResourceStatus
    metadata: dict[str, Any] = Field(validation_alias="resource_metadata")
    created_at: datetime
    updated_at: datetime


class NodeStateSummary(BaseModel):
    recall: float = 0
    explanation: float = 0
    application: float = 0
    stability: float = 0
    confidence: float = 0


class PathNodeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: UUID
    learning_path_id: UUID
    concept_id: UUID | None
    node_type: NodeType
    title: str
    description: str | None
    position_x: float | None
    position_y: float | None
    status: NodeStatus
    importance: NodeImportance
    estimated_minutes: int | None
    completion_policy: dict[str, Any]
    metadata: dict[str, Any] = Field(validation_alias="node_metadata")
    created_at: datetime
    updated_at: datetime


class PathNodeDetailResponse(PathNodeResponse):
    resources: list[NodeResourceResponse]
    state: NodeStateSummary | None
    completion_met: bool
    completion_blockers: list[str]
    blocked_reasons: list[str]


class PathEdgeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    learning_path_id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: EdgeType
    condition: dict[str, Any] | None
    label: str | None
    created_at: datetime


class SuggestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    learning_path_id: UUID
    suggestion_type: SuggestionType
    payload: dict[str, Any]
    rationale: str
    source: SuggestionSource
    status: SuggestionStatus
    created_at: datetime
    resolved_at: datetime | None


class PathVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    learning_path_id: UUID
    version: int
    snapshot: dict[str, Any]
    change_summary: str
    change_source: str
    created_at: datetime


class GoalSummary(BaseModel):
    id: UUID
    title: str
    description: str | None


class ProgressSummary(BaseModel):
    completed: int
    total: int
    required_completed: int
    required_total: int
    percent: float


class LearningPathDetailResponse(BaseModel):
    path: LearningPathResponse
    goal: GoalSummary
    nodes: list[PathNodeDetailResponse]
    edges: list[PathEdgeResponse]
    progress: ProgressSummary
    current_node: PathNodeDetailResponse | None
    available_next_node_ids: list[UUID]
    pending_suggestions: list[SuggestionResponse]
    latest_version: PathVersionResponse | None


class MutationResult(BaseModel):
    path_version: int


class NodeMutationResult(MutationResult):
    node: PathNodeResponse


class EdgeMutationResult(MutationResult):
    edge: PathEdgeResponse


class ResourceMutationResult(MutationResult):
    resource: NodeResourceResponse
