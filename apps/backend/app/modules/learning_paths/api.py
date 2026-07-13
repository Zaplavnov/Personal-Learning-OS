from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.modules.learning_paths.application import LearningPathService
from app.modules.learning_paths.infrastructure import SqlAlchemyLearningPathRepository
from app.modules.learning_paths.planner import RuleBasedLearningPathPlanner
from app.modules.learning_paths.schemas import (
    EdgeCreate,
    EdgeMutationResult,
    EdgeUpdate,
    GenerateDraftRequest,
    GoalSummary,
    LearningPathCreate,
    LearningPathDetailResponse,
    LearningPathResponse,
    LearningPathUpdate,
    MutationResult,
    NodeCreate,
    NodeMutationResult,
    NodeResourceResponse,
    NodeStateSummary,
    NodeUpdate,
    PathEdgeResponse,
    PathNodeDetailResponse,
    PathNodeResponse,
    PathVersionResponse,
    ProgressSummary,
    ResourceCreate,
    ResourceMutationResult,
    ResourceUpdate,
    RestoreVersionRequest,
    SuggestionCreate,
    SuggestionResponse,
    VersionedMutation,
)

router = APIRouter(tags=["learning-paths"])


def get_learning_path_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> LearningPathService:
    return LearningPathService(
        SqlAlchemyLearningPathRepository(session), RuleBasedLearningPathPlanner()
    )


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Service = Annotated[LearningPathService, Depends(get_learning_path_service)]


def node_response(item: dict[str, Any]) -> PathNodeDetailResponse:
    state = item["state"]
    return PathNodeDetailResponse(
        **PathNodeResponse.model_validate(item["node"]).model_dump(),
        resources=[NodeResourceResponse.model_validate(resource) for resource in item["resources"]],
        state=(
            NodeStateSummary(
                recall=state.recall,
                explanation=state.explanation,
                application=state.application,
                stability=state.stability,
                confidence=state.confidence,
            )
            if state
            else None
        ),
        completion_met=item["completion_met"],
        completion_blockers=item["completion_blockers"],
        blocked_reasons=item["blocked_reasons"],
    )


async def detail_response(
    service: LearningPathService, user_id: UUID, path_id: UUID
) -> LearningPathDetailResponse:
    detail = await service.get_detail(user_id, path_id)
    nodes = [node_response(item) for item in detail["nodes"]]
    current = next((node for node in nodes if node.id == detail["current_node_id"]), None)
    return LearningPathDetailResponse(
        path=LearningPathResponse.model_validate(detail["path"]),
        goal=GoalSummary(
            id=detail["goal"].id,
            title=detail["goal"].title,
            description=detail["goal"].description,
        ),
        nodes=nodes,
        edges=[PathEdgeResponse.model_validate(item) for item in detail["edges"]],
        progress=ProgressSummary(**detail["progress"]),
        current_node=current,
        available_next_node_ids=detail["available"],
        pending_suggestions=[
            SuggestionResponse.model_validate(item) for item in detail["suggestions"]
        ],
        latest_version=(
            PathVersionResponse.model_validate(detail["latest_version"])
            if detail["latest_version"]
            else None
        ),
    )


@router.post(
    "/learning-goals/{goal_id}/path/generate-draft",
    response_model=LearningPathDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_draft(
    goal_id: UUID,
    payload: GenerateDraftRequest,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathDetailResponse:
    path = await service.generate_draft(user_id, goal_id, **payload.model_dump())
    return await detail_response(service, user_id, path.id)


@router.get("/learning-goals/{goal_id}/path", response_model=LearningPathResponse | None)
async def get_goal_path(
    goal_id: UUID, user_id: CurrentUserId, service: Service
) -> LearningPathResponse | None:
    path = await service.get_goal_path(user_id, goal_id)
    return LearningPathResponse.model_validate(path) if path else None


@router.post(
    "/learning-paths",
    response_model=LearningPathDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_path(
    payload: LearningPathCreate, user_id: CurrentUserId, service: Service
) -> LearningPathDetailResponse:
    path = await service.create_empty(user_id, **payload.model_dump())
    return await detail_response(service, user_id, path.id)


@router.get("/learning-paths/{path_id}", response_model=LearningPathDetailResponse)
async def get_path(
    path_id: UUID, user_id: CurrentUserId, service: Service
) -> LearningPathDetailResponse:
    return await detail_response(service, user_id, path_id)


@router.patch("/learning-paths/{path_id}", response_model=LearningPathResponse)
async def update_path(
    path_id: UUID,
    payload: LearningPathUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathResponse:
    path = await service.update_path(
        user_id,
        path_id,
        payload.expected_version,
        payload.model_dump(exclude_unset=True),
    )
    return LearningPathResponse.model_validate(path)


@router.post("/learning-paths/{path_id}/publish", response_model=LearningPathDetailResponse)
async def publish_path(
    path_id: UUID,
    payload: VersionedMutation,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathDetailResponse:
    await service.publish(user_id, path_id, payload.expected_version)
    return await detail_response(service, user_id, path_id)


@router.post(
    "/learning-paths/{path_id}/nodes",
    response_model=NodeMutationResult,
    status_code=status.HTTP_201_CREATED,
)
async def add_node(
    path_id: UUID, payload: NodeCreate, user_id: CurrentUserId, service: Service
) -> NodeMutationResult:
    node, version = await service.add_node(
        user_id, path_id, payload.expected_version, payload.model_dump()
    )
    return NodeMutationResult(path_version=version, node=PathNodeResponse.model_validate(node))


@router.patch("/learning-paths/{path_id}/nodes/{node_id}", response_model=NodeMutationResult)
async def update_node(
    path_id: UUID,
    node_id: UUID,
    payload: NodeUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> NodeMutationResult:
    node, version = await service.update_node(
        user_id,
        path_id,
        node_id,
        payload.expected_version,
        payload.model_dump(exclude_unset=True),
    )
    return NodeMutationResult(path_version=version, node=PathNodeResponse.model_validate(node))


@router.delete("/learning-paths/{path_id}/nodes/{node_id}", response_model=MutationResult)
async def delete_node(
    path_id: UUID,
    node_id: UUID,
    expected_version: Annotated[int, Query(ge=0)],
    user_id: CurrentUserId,
    service: Service,
) -> MutationResult:
    version = await service.delete_node(user_id, path_id, node_id, expected_version)
    return MutationResult(path_version=version)


@router.post(
    "/learning-paths/{path_id}/edges",
    response_model=EdgeMutationResult,
    status_code=status.HTTP_201_CREATED,
)
async def add_edge(
    path_id: UUID, payload: EdgeCreate, user_id: CurrentUserId, service: Service
) -> EdgeMutationResult:
    edge, version = await service.add_edge(
        user_id, path_id, payload.expected_version, payload.model_dump()
    )
    return EdgeMutationResult(path_version=version, edge=PathEdgeResponse.model_validate(edge))


@router.patch("/learning-paths/{path_id}/edges/{edge_id}", response_model=EdgeMutationResult)
async def update_edge(
    path_id: UUID,
    edge_id: UUID,
    payload: EdgeUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> EdgeMutationResult:
    edge, version = await service.update_edge(
        user_id,
        path_id,
        edge_id,
        payload.expected_version,
        payload.model_dump(exclude_unset=True),
    )
    return EdgeMutationResult(path_version=version, edge=PathEdgeResponse.model_validate(edge))


@router.delete("/learning-paths/{path_id}/edges/{edge_id}", response_model=MutationResult)
async def delete_edge(
    path_id: UUID,
    edge_id: UUID,
    expected_version: Annotated[int, Query(ge=0)],
    user_id: CurrentUserId,
    service: Service,
) -> MutationResult:
    return MutationResult(
        path_version=await service.delete_edge(user_id, path_id, edge_id, expected_version)
    )


@router.post(
    "/learning-paths/{path_id}/nodes/{node_id}/resources",
    response_model=ResourceMutationResult,
    status_code=status.HTTP_201_CREATED,
)
async def add_resource(
    path_id: UUID,
    node_id: UUID,
    payload: ResourceCreate,
    user_id: CurrentUserId,
    service: Service,
) -> ResourceMutationResult:
    resource, version = await service.add_resource(
        user_id, path_id, node_id, payload.expected_version, payload.model_dump()
    )
    return ResourceMutationResult(
        path_version=version,
        resource=NodeResourceResponse.model_validate(resource),
    )


@router.patch(
    "/learning-paths/{path_id}/resources/{resource_id}",
    response_model=ResourceMutationResult,
)
async def update_resource(
    path_id: UUID,
    resource_id: UUID,
    payload: ResourceUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> ResourceMutationResult:
    resource, version = await service.update_resource(
        user_id,
        path_id,
        resource_id,
        payload.expected_version,
        payload.model_dump(exclude_unset=True),
    )
    return ResourceMutationResult(
        path_version=version,
        resource=NodeResourceResponse.model_validate(resource),
    )


@router.delete("/learning-paths/{path_id}/resources/{resource_id}", response_model=MutationResult)
async def delete_resource(
    path_id: UUID,
    resource_id: UUID,
    expected_version: Annotated[int, Query(ge=0)],
    user_id: CurrentUserId,
    service: Service,
) -> MutationResult:
    return MutationResult(
        path_version=await service.delete_resource(user_id, path_id, resource_id, expected_version)
    )


@router.post(
    "/learning-paths/{path_id}/nodes/{node_id}/complete",
    response_model=LearningPathDetailResponse,
)
async def complete_node(
    path_id: UUID,
    node_id: UUID,
    payload: VersionedMutation,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathDetailResponse:
    await service.complete_node(user_id, path_id, node_id, payload.expected_version)
    return await detail_response(service, user_id, path_id)


@router.post(
    "/learning-paths/{path_id}/nodes/{node_id}/skip",
    response_model=LearningPathDetailResponse,
)
async def skip_node(
    path_id: UUID,
    node_id: UUID,
    payload: VersionedMutation,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathDetailResponse:
    await service.skip_node(user_id, path_id, node_id, payload.expected_version)
    return await detail_response(service, user_id, path_id)


@router.post(
    "/learning-paths/{path_id}/suggestions",
    response_model=SuggestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_suggestion(
    path_id: UUID,
    payload: SuggestionCreate,
    user_id: CurrentUserId,
    service: Service,
) -> SuggestionResponse:
    suggestion = await service.create_suggestion(
        user_id, path_id, payload.expected_version, payload.model_dump()
    )
    return SuggestionResponse.model_validate(suggestion)


@router.post(
    "/learning-path-suggestions/{suggestion_id}/accept",
    response_model=LearningPathDetailResponse,
)
async def accept_suggestion(
    suggestion_id: UUID,
    payload: VersionedMutation,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathDetailResponse:
    path = await service.accept_suggestion(user_id, suggestion_id, payload.expected_version)
    return await detail_response(service, user_id, path.id)


@router.post(
    "/learning-path-suggestions/{suggestion_id}/reject",
    response_model=SuggestionResponse,
)
async def reject_suggestion(
    suggestion_id: UUID,
    payload: VersionedMutation,
    user_id: CurrentUserId,
    service: Service,
) -> SuggestionResponse:
    suggestion = await service.reject_suggestion(user_id, suggestion_id, payload.expected_version)
    return SuggestionResponse.model_validate(suggestion)


@router.get("/learning-paths/{path_id}/versions", response_model=list[PathVersionResponse])
async def list_versions(
    path_id: UUID, user_id: CurrentUserId, service: Service
) -> list[PathVersionResponse]:
    return [
        PathVersionResponse.model_validate(item)
        for item in await service.list_versions(user_id, path_id)
    ]


@router.get("/learning-paths/{path_id}/versions/{version}", response_model=PathVersionResponse)
async def get_version(
    path_id: UUID, version: int, user_id: CurrentUserId, service: Service
) -> PathVersionResponse:
    return PathVersionResponse.model_validate(await service.get_version(user_id, path_id, version))


@router.post(
    "/learning-paths/{path_id}/versions/{version}/restore",
    response_model=LearningPathDetailResponse,
)
async def restore_version(
    path_id: UUID,
    version: int,
    payload: RestoreVersionRequest,
    user_id: CurrentUserId,
    service: Service,
) -> LearningPathDetailResponse:
    await service.restore_version(
        user_id,
        path_id,
        version,
        payload.expected_version,
        payload.change_summary,
    )
    return await detail_response(service, user_id, path_id)
