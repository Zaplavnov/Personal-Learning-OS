from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.modules.learning_paths.domain import (
    EdgeType,
    GraphEdge,
    NodeImportance,
    NodeStatus,
    NodeType,
    PathStatus,
    ResourceStatus,
    SuggestionStatus,
    assert_acyclic,
    available_nodes,
    evaluate_completion_policy,
)
from app.modules.learning_paths.infrastructure import (
    LearningPath,
    LearningPathEdge,
    LearningPathNode,
    LearningPathNodeResource,
    LearningPathSuggestion,
    LearningPathVersion,
    SqlAlchemyLearningPathRepository,
)
from app.modules.learning_paths.planner import (
    LearningPathPlanner,
    PlannerConcept,
    PlannerMaterial,
    PlannerRelation,
    PlannerState,
)
from app.modules.outbox.models import OutboxEvent


class LearningPathService:
    def __init__(
        self,
        repository: SqlAlchemyLearningPathRepository,
        planner: LearningPathPlanner,
    ) -> None:
        self.repository = repository
        self.planner = planner

    async def generate_draft(
        self,
        user_id: UUID,
        goal_id: UUID,
        *,
        target_concept_ids: list[UUID],
        max_depth: int,
        title: str | None,
    ) -> LearningPath:
        goal = await self.repository.get_goal(user_id, goal_id)
        if goal is None:
            raise ApiError(
                "learning_goal_not_found", "Learning goal was not found", status_code=404
            )
        concepts = await self.repository.list_concepts(user_id, goal.learning_space_id)
        by_id = {concept.id: concept for concept in concepts}
        if any(concept_id not in by_id for concept_id in target_concept_ids):
            raise ApiError(
                "invalid_target_concept",
                "Every target concept must belong to the goal learning space",
                status_code=422,
            )
        relations = await self.repository.list_concept_relations(user_id, goal.learning_space_id)
        states = await self.repository.get_states(list(by_id))
        materials = await self.repository.list_materials(user_id, goal.learning_space_id)
        path = LearningPath(
            id=uuid4(),
            user_id=user_id,
            learning_space_id=goal.learning_space_id,
            learning_goal_id=goal.id,
            title=title or f"Путь: {goal.title}",
            description="Rule-based draft built from target concepts and prerequisites.",
            status=PathStatus.DRAFT.value,
            version=0,
        )
        self.repository.add(path)
        plan = self.planner.build(
            path_id=path.id,
            target_concept_ids=target_concept_ids,
            concepts=[PlannerConcept(item.id, item.title, item.description) for item in concepts],
            relations=[
                PlannerRelation(item.source_concept_id, item.target_concept_id, item.relation_type)
                for item in relations
            ],
            states={
                concept_id: PlannerState(
                    concept_id,
                    state.explanation,
                    state.application,
                    state.stability,
                )
                for concept_id, state in states.items()
            },
            materials=[
                PlannerMaterial(
                    item.id,
                    item.title,
                    item.estimated_minutes,
                    item.material_metadata,
                )
                for item in materials
            ],
            max_depth=max_depth,
        )
        for item in plan.nodes:
            self.repository.add(
                LearningPathNode(
                    id=item.id,
                    learning_path_id=path.id,
                    concept_id=item.concept_id,
                    node_type=NodeType.CONCEPT.value,
                    title=item.title,
                    description=item.description,
                    position_x=item.position_x,
                    position_y=item.position_y,
                    status=item.status,
                    importance=item.importance,
                    estimated_minutes=item.estimated_minutes,
                    completion_policy=item.completion_policy,
                    node_metadata={**item.metadata, "draft_rationale": plan.rationale},
                )
            )
        await self.repository.flush()
        for item in plan.edges:
            self.repository.add(
                LearningPathEdge(
                    id=item.id,
                    learning_path_id=path.id,
                    source_node_id=item.source_node_id,
                    target_node_id=item.target_node_id,
                    edge_type=item.edge_type,
                )
            )
        for item in plan.resources:
            self.repository.add(
                LearningPathNodeResource(
                    id=item.id,
                    node_id=item.node_id,
                    resource_type=item.resource_type,
                    resource_id=item.resource_id,
                    title=item.title,
                    is_required=item.is_required,
                    order_index=item.order_index,
                    completion_status=ResourceStatus.PLANNED.value,
                    resource_metadata={"attached_by": "rule_engine"},
                )
            )
        self.repository.add(self._event("learning_path.created", path.id, user_id))
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def create_empty(
        self,
        user_id: UUID,
        *,
        learning_goal_id: UUID,
        title: str,
        description: str | None,
    ) -> LearningPath:
        goal = await self.repository.get_goal(user_id, learning_goal_id)
        if goal is None:
            raise ApiError(
                "learning_goal_not_found", "Learning goal was not found", status_code=404
            )
        path = LearningPath(
            id=uuid4(),
            user_id=user_id,
            learning_space_id=goal.learning_space_id,
            learning_goal_id=goal.id,
            title=title,
            description=description,
            status=PathStatus.DRAFT.value,
            version=0,
        )
        self.repository.add(path)
        self.repository.add(self._event("learning_path.created", path.id, user_id))
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def get_goal_path(self, user_id: UUID, goal_id: UUID) -> LearningPath | None:
        if await self.repository.get_goal(user_id, goal_id) is None:
            raise ApiError(
                "learning_goal_not_found", "Learning goal was not found", status_code=404
            )
        return await self.repository.get_goal_path(user_id, goal_id)

    async def get_detail(self, user_id: UUID, path_id: UUID) -> dict[str, Any]:
        path = await self._require_path(user_id, path_id)
        goal = await self.repository.get_goal(user_id, path.learning_goal_id)
        nodes = await self.repository.list_nodes(path.id)
        edges = await self.repository.list_edges(path.id)
        resources = await self.repository.list_resources(path.id)
        suggestions = await self.repository.list_suggestions(path.id, pending_only=True)
        versions = await self.repository.list_versions(path.id)
        states = await self.repository.get_states(
            [node.concept_id for node in nodes if node.concept_id is not None]
        )
        resources_by_node: dict[UUID, list[LearningPathNodeResource]] = {}
        for resource in resources:
            resources_by_node.setdefault(resource.node_id, []).append(resource)
        graph_edges = self._graph_edges(edges)
        completed = {
            node.id
            for node in nodes
            if node.status in (NodeStatus.COMPLETED.value, NodeStatus.SKIPPED.value)
        }
        available = available_nodes({node.id for node in nodes}, graph_edges, completed)
        incoming: dict[UUID, list[LearningPathNode]] = {node.id: [] for node in nodes}
        by_node_id = {node.id: node for node in nodes}
        for edge in edges:
            if edge.edge_type != EdgeType.RETURNS_TO.value:
                incoming[edge.target_node_id].append(by_node_id[edge.source_node_id])
        details = []
        for node in nodes:
            state = states.get(node.concept_id) if node.concept_id else None
            resource_counts: dict[str, int] = {}
            for resource in resources_by_node.get(node.id, []):
                if resource.completion_status == ResourceStatus.COMPLETED.value:
                    resource_counts[resource.resource_type] = (
                        resource_counts.get(resource.resource_type, 0) + 1
                    )
            dimensions = self._dimensions(state)
            evidence_counts = (
                await self.repository.evidence_counts(node.concept_id) if node.concept_id else {}
            )
            completion_met, blockers = evaluate_completion_policy(
                node.completion_policy,
                resource_counts=resource_counts,
                dimensions=dimensions,
                evidence_counts=evidence_counts,
            )
            blocked_reasons = [
                f"Сначала завершить: {predecessor.title}"
                for predecessor in incoming[node.id]
                if predecessor.id not in completed
            ]
            details.append(
                {
                    "node": node,
                    "resources": resources_by_node.get(node.id, []),
                    "state": state,
                    "completion_met": completion_met,
                    "completion_blockers": blockers,
                    "blocked_reasons": blocked_reasons,
                }
            )
        required = [node for node in nodes if node.importance == NodeImportance.REQUIRED.value]
        completed_nodes = [node for node in nodes if node.status == NodeStatus.COMPLETED.value]
        required_completed = [
            node for node in required if node.status == NodeStatus.COMPLETED.value
        ]
        return {
            "path": path,
            "goal": goal,
            "nodes": details,
            "edges": edges,
            "progress": {
                "completed": len(completed_nodes),
                "total": len(nodes),
                "required_completed": len(required_completed),
                "required_total": len(required),
                "percent": round(len(completed_nodes) / len(nodes) * 100, 2) if nodes else 0,
            },
            "current_node_id": path.current_node_id,
            "available": sorted(available, key=str),
            "suggestions": suggestions,
            "latest_version": versions[0] if versions else None,
        }

    async def update_path(
        self, user_id: UUID, path_id: UUID, expected_version: int, changes: dict[str, Any]
    ) -> LearningPath:
        path = await self._locked_path(user_id, path_id, expected_version)
        for field, value in changes.items():
            if field != "expected_version":
                setattr(path, field, value.value if hasattr(value, "value") else value)
        await self._finish_structure_change(path, user_id, "Path metadata updated", "user")
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def publish(self, user_id: UUID, path_id: UUID, expected_version: int) -> LearningPath:
        path = await self._locked_path(user_id, path_id, expected_version)
        nodes = await self.repository.list_nodes(path.id)
        if not nodes:
            raise ApiError("empty_learning_path", "Cannot publish an empty path", status_code=409)
        edges = await self.repository.list_edges(path.id)
        self._assert_valid_graph(nodes, edges)
        await self.repository.archive_active_path(path.learning_goal_id, path.id)
        path.status = PathStatus.ACTIVE.value
        await self._advance(path, nodes, edges, user_id)
        await self._suggest_missing_prerequisites(path, user_id)
        await self._finish_structure_change(path, user_id, "Learning path published", "system")
        self.repository.add(self._event("learning_path.published", path.id, user_id))
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def add_node(
        self, user_id: UUID, path_id: UUID, expected_version: int, data: dict[str, Any]
    ) -> tuple[LearningPathNode, int]:
        path = await self._locked_path(user_id, path_id, expected_version)
        concept_id = data.get("concept_id")
        node_type = data["node_type"]
        node_type_value = node_type.value if hasattr(node_type, "value") else node_type
        if node_type_value == NodeType.CONCEPT.value:
            await self._validate_concept(path, user_id, concept_id)
        node = LearningPathNode(
            id=uuid4(),
            learning_path_id=path.id,
            concept_id=concept_id,
            node_type=node_type_value,
            title=data["title"],
            description=data.get("description"),
            position_x=data.get("position_x"),
            position_y=data.get("position_y"),
            status=self._value(data.get("status", NodeStatus.PLANNED)),
            importance=self._value(data.get("importance", NodeImportance.REQUIRED)),
            estimated_minutes=data.get("estimated_minutes"),
            completion_policy=data.get("completion_policy", {}),
            node_metadata=data.get("metadata", {}),
        )
        self.repository.add(node)
        await self.repository.flush()
        await self._finish_structure_change(path, user_id, f"Added node: {node.title}", "user")
        await self.repository.commit()
        await self.repository.refresh(node)
        return node, path.version

    async def update_node(
        self,
        user_id: UUID,
        path_id: UUID,
        node_id: UUID,
        expected_version: int,
        changes: dict[str, Any],
    ) -> tuple[LearningPathNode, int]:
        path = await self._locked_path(user_id, path_id, expected_version)
        node = await self._require_node(path.id, node_id)
        if "concept_id" in changes:
            await self._validate_concept(path, user_id, changes["concept_id"])
        aliases = {"metadata": "node_metadata"}
        for field, value in changes.items():
            if field != "expected_version":
                setattr(node, aliases.get(field, field), self._value(value))
        await self._finish_structure_change(path, user_id, f"Updated node: {node.title}", "user")
        await self.repository.commit()
        await self.repository.refresh(node)
        return node, path.version

    async def delete_node(
        self, user_id: UUID, path_id: UUID, node_id: UUID, expected_version: int
    ) -> int:
        path = await self._locked_path(user_id, path_id, expected_version)
        node = await self._require_node(path.id, node_id)
        if path.current_node_id == node.id:
            path.current_node_id = None
        title = node.title
        await self.repository.delete(node)
        await self.repository.flush()
        await self._finish_structure_change(path, user_id, f"Removed node: {title}", "user")
        await self.repository.commit()
        return path.version

    async def add_edge(
        self, user_id: UUID, path_id: UUID, expected_version: int, data: dict[str, Any]
    ) -> tuple[LearningPathEdge, int]:
        path = await self._locked_path(user_id, path_id, expected_version)
        source = await self._require_node(path.id, data["source_node_id"])
        target = await self._require_node(path.id, data["target_node_id"])
        edge_type = self._value(data["edge_type"])
        edges = await self.repository.list_edges(path.id)
        if any(
            edge.source_node_id == source.id
            and edge.target_node_id == target.id
            and edge.edge_type == edge_type
            for edge in edges
        ):
            raise ApiError("learning_path_edge_exists", "Duplicate path edge", status_code=409)
        candidate = LearningPathEdge(
            id=uuid4(),
            learning_path_id=path.id,
            source_node_id=source.id,
            target_node_id=target.id,
            edge_type=edge_type,
            condition=data.get("condition"),
            label=data.get("label"),
        )
        self._assert_valid_graph(await self.repository.list_nodes(path.id), [*edges, candidate])
        self.repository.add(candidate)
        await self.repository.flush()
        await self._finish_structure_change(path, user_id, "Connected path nodes", "user")
        await self.repository.commit()
        await self.repository.refresh(candidate)
        return candidate, path.version

    async def update_edge(
        self,
        user_id: UUID,
        path_id: UUID,
        edge_id: UUID,
        expected_version: int,
        changes: dict[str, Any],
    ) -> tuple[LearningPathEdge, int]:
        path = await self._locked_path(user_id, path_id, expected_version)
        edge = await self.repository.get_edge(path.id, edge_id)
        if edge is None:
            raise ApiError(
                "learning_path_edge_not_found", "Path edge was not found", status_code=404
            )
        for field, value in changes.items():
            if field != "expected_version":
                setattr(edge, field, self._value(value))
        self._assert_valid_graph(
            await self.repository.list_nodes(path.id), await self.repository.list_edges(path.id)
        )
        await self._finish_structure_change(path, user_id, "Updated path edge", "user")
        await self.repository.commit()
        await self.repository.refresh(edge)
        return edge, path.version

    async def delete_edge(
        self, user_id: UUID, path_id: UUID, edge_id: UUID, expected_version: int
    ) -> int:
        path = await self._locked_path(user_id, path_id, expected_version)
        edge = await self.repository.get_edge(path.id, edge_id)
        if edge is None:
            raise ApiError(
                "learning_path_edge_not_found", "Path edge was not found", status_code=404
            )
        await self.repository.delete(edge)
        await self._finish_structure_change(path, user_id, "Removed path edge", "user")
        await self.repository.commit()
        return path.version

    async def add_resource(
        self,
        user_id: UUID,
        path_id: UUID,
        node_id: UUID,
        expected_version: int,
        data: dict[str, Any],
    ) -> tuple[LearningPathNodeResource, int]:
        path = await self._locked_path(user_id, path_id, expected_version)
        await self._require_node(path.id, node_id)
        resource_type = self._value(data["resource_type"])
        if resource_type == "material" and (
            data.get("resource_id") is None
            or not await self.repository.owns_material(user_id, data["resource_id"])
        ):
            raise ApiError("material_not_found", "Material was not found", status_code=404)
        resource = LearningPathNodeResource(
            id=uuid4(),
            node_id=node_id,
            resource_type=resource_type,
            resource_id=data.get("resource_id"),
            title=data["title"],
            is_required=data.get("is_required", False),
            order_index=data.get("order_index", 0),
            completion_status=self._value(data.get("completion_status", ResourceStatus.PLANNED)),
            resource_metadata=data.get("metadata", {}),
        )
        self.repository.add(resource)
        await self.repository.flush()
        await self._finish_structure_change(
            path, user_id, f"Attached resource: {resource.title}", "user"
        )
        await self.repository.commit()
        await self.repository.refresh(resource)
        return resource, path.version

    async def update_resource(
        self,
        user_id: UUID,
        path_id: UUID,
        resource_id: UUID,
        expected_version: int,
        changes: dict[str, Any],
    ) -> tuple[LearningPathNodeResource, int]:
        path = await self._locked_path(user_id, path_id, expected_version)
        resource = await self.repository.get_resource(path.id, resource_id)
        if resource is None:
            raise ApiError(
                "path_resource_not_found", "Path resource was not found", status_code=404
            )
        aliases = {"metadata": "resource_metadata"}
        for field, value in changes.items():
            if field != "expected_version":
                setattr(resource, aliases.get(field, field), self._value(value))
        await self._finish_structure_change(
            path, user_id, f"Updated resource: {resource.title}", "user"
        )
        await self.repository.commit()
        await self.repository.refresh(resource)
        return resource, path.version

    async def delete_resource(
        self, user_id: UUID, path_id: UUID, resource_id: UUID, expected_version: int
    ) -> int:
        path = await self._locked_path(user_id, path_id, expected_version)
        resource = await self.repository.get_resource(path.id, resource_id)
        if resource is None:
            raise ApiError(
                "path_resource_not_found", "Path resource was not found", status_code=404
            )
        await self.repository.delete(resource)
        await self._finish_structure_change(path, user_id, "Removed path resource", "user")
        await self.repository.commit()
        return path.version

    async def complete_node(
        self, user_id: UUID, path_id: UUID, node_id: UUID, expected_version: int
    ) -> LearningPath:
        path = await self._locked_path(user_id, path_id, expected_version)
        node = await self._require_node(path.id, node_id)
        if node.status == NodeStatus.COMPLETED.value:
            return path
        resources = [
            item
            for item in await self.repository.list_resources(path.id)
            if item.node_id == node.id
        ]
        resource_counts: dict[str, int] = {}
        for resource in resources:
            if resource.completion_status == ResourceStatus.COMPLETED.value:
                resource_counts[resource.resource_type] = (
                    resource_counts.get(resource.resource_type, 0) + 1
                )
        state = (
            (await self.repository.get_states([node.concept_id])).get(node.concept_id)
            if node.concept_id
            else None
        )
        evidence_counts = (
            await self.repository.evidence_counts(node.concept_id) if node.concept_id else {}
        )
        passed, blockers = evaluate_completion_policy(
            node.completion_policy,
            resource_counts=resource_counts,
            dimensions=self._dimensions(state),
            evidence_counts=evidence_counts,
        )
        if not passed:
            raise ApiError(
                "node_completion_policy_not_met",
                "Node completion policy is not met",
                status_code=409,
                details={"blockers": blockers},
            )
        node.status = NodeStatus.COMPLETED.value
        nodes = await self.repository.list_nodes(path.id)
        edges = await self.repository.list_edges(path.id)
        await self._advance(path, nodes, edges, user_id)
        await self._suggest_missing_prerequisites(path, user_id)
        await self._finish_structure_change(path, user_id, f"Completed node: {node.title}", "user")
        self.repository.add(
            self._event("learning_path.node_completed", path.id, user_id, {"node_id": str(node.id)})
        )
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def skip_node(
        self, user_id: UUID, path_id: UUID, node_id: UUID, expected_version: int
    ) -> LearningPath:
        path = await self._locked_path(user_id, path_id, expected_version)
        node = await self._require_node(path.id, node_id)
        if node.importance == NodeImportance.REQUIRED.value:
            raise ApiError(
                "required_node_cannot_be_skipped",
                "Required node cannot be skipped",
                status_code=409,
            )
        node.status = NodeStatus.SKIPPED.value
        await self._advance(
            path,
            await self.repository.list_nodes(path.id),
            await self.repository.list_edges(path.id),
            user_id,
        )
        await self._suggest_missing_prerequisites(path, user_id)
        await self._finish_structure_change(path, user_id, f"Skipped node: {node.title}", "user")
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def create_suggestion(
        self, user_id: UUID, path_id: UUID, expected_version: int, data: dict[str, Any]
    ) -> LearningPathSuggestion:
        path = await self._locked_path(user_id, path_id, expected_version)
        suggestion = LearningPathSuggestion(
            id=uuid4(),
            learning_path_id=path.id,
            suggestion_type=self._value(data["suggestion_type"]),
            payload={**data["payload"], "base_version": path.version},
            rationale=data["rationale"],
            source=self._value(data["source"]),
            status=SuggestionStatus.PENDING.value,
        )
        self.repository.add(suggestion)
        self.repository.add(
            self._event(
                "learning_path.suggestion_created",
                path.id,
                user_id,
                {"suggestion_id": str(suggestion.id)},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(suggestion)
        return suggestion

    async def accept_suggestion(
        self, user_id: UUID, suggestion_id: UUID, expected_version: int
    ) -> LearningPath:
        suggestion = await self.repository.get_suggestion(user_id, suggestion_id, lock=True)
        if suggestion is None:
            raise ApiError("path_suggestion_not_found", "Suggestion was not found", status_code=404)
        if suggestion.status != SuggestionStatus.PENDING.value:
            raise ApiError("suggestion_resolved", "Suggestion is already resolved", status_code=409)
        path = await self._locked_path(user_id, suggestion.learning_path_id, expected_version)
        await self._apply_suggestion(path, suggestion, user_id)
        suggestion.status = SuggestionStatus.ACCEPTED.value
        suggestion.resolved_at = datetime.now(UTC)
        await self.repository.flush()
        await self._finish_structure_change(
            path,
            user_id,
            f"Accepted suggestion: {suggestion.suggestion_type}",
            "accepted_suggestion",
        )
        self.repository.add(
            self._event(
                "learning_path.suggestion_accepted",
                path.id,
                user_id,
                {"suggestion_id": str(suggestion.id)},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def reject_suggestion(
        self, user_id: UUID, suggestion_id: UUID, expected_version: int
    ) -> LearningPathSuggestion:
        suggestion = await self.repository.get_suggestion(user_id, suggestion_id, lock=True)
        if suggestion is None:
            raise ApiError("path_suggestion_not_found", "Suggestion was not found", status_code=404)
        path = await self._locked_path(user_id, suggestion.learning_path_id, expected_version)
        if suggestion.status != SuggestionStatus.PENDING.value:
            raise ApiError("suggestion_resolved", "Suggestion is already resolved", status_code=409)
        suggestion.status = SuggestionStatus.REJECTED.value
        suggestion.resolved_at = datetime.now(UTC)
        self.repository.add(
            self._event(
                "learning_path.suggestion_rejected",
                path.id,
                user_id,
                {"suggestion_id": str(suggestion.id)},
            )
        )
        await self.repository.commit()
        await self.repository.refresh(suggestion)
        return suggestion

    async def list_versions(self, user_id: UUID, path_id: UUID) -> list[LearningPathVersion]:
        await self._require_path(user_id, path_id)
        return await self.repository.list_versions(path_id)

    async def get_version(self, user_id: UUID, path_id: UUID, version: int) -> LearningPathVersion:
        await self._require_path(user_id, path_id)
        result = await self.repository.get_version(path_id, version)
        if result is None:
            raise ApiError("path_version_not_found", "Path version was not found", status_code=404)
        return result

    async def restore_version(
        self,
        user_id: UUID,
        path_id: UUID,
        version: int,
        expected_version: int,
        change_summary: str,
    ) -> LearningPath:
        path = await self._locked_path(user_id, path_id, expected_version)
        stored = await self.repository.get_version(path.id, version)
        if stored is None:
            raise ApiError("path_version_not_found", "Path version was not found", status_code=404)
        snapshot = stored.snapshot
        path.title = snapshot["path"]["title"]
        path.description = snapshot["path"].get("description")
        path.current_node_id = None
        await self.repository.flush()
        await self.repository.delete_graph(path.id)
        await self.repository.flush()
        for item in snapshot["nodes"]:
            self.repository.add(
                LearningPathNode(
                    id=UUID(item["id"]),
                    learning_path_id=path.id,
                    concept_id=UUID(item["concept_id"]) if item["concept_id"] else None,
                    node_type=item["node_type"],
                    title=item["title"],
                    description=item["description"],
                    position_x=item["position_x"],
                    position_y=item["position_y"],
                    status=item["status"],
                    importance=item["importance"],
                    estimated_minutes=item["estimated_minutes"],
                    completion_policy=item["completion_policy"],
                    node_metadata=item["metadata"],
                )
            )
        await self.repository.flush()
        for item in snapshot["edges"]:
            self.repository.add(
                LearningPathEdge(
                    id=UUID(item["id"]),
                    learning_path_id=path.id,
                    source_node_id=UUID(item["source_node_id"]),
                    target_node_id=UUID(item["target_node_id"]),
                    edge_type=item["edge_type"],
                    condition=item["condition"],
                    label=item["label"],
                )
            )
        for item in snapshot["resources"]:
            self.repository.add(
                LearningPathNodeResource(
                    id=UUID(item["id"]),
                    node_id=UUID(item["node_id"]),
                    resource_type=item["resource_type"],
                    resource_id=UUID(item["resource_id"]) if item["resource_id"] else None,
                    title=item["title"],
                    is_required=item["is_required"],
                    order_index=item["order_index"],
                    completion_status=item["completion_status"],
                    resource_metadata=item["metadata"],
                )
            )
        await self.repository.flush()
        current_id = snapshot.get("current_node_id")
        path.current_node_id = UUID(current_id) if current_id else None
        await self._finish_structure_change(path, user_id, change_summary, "user")
        await self.repository.commit()
        await self.repository.refresh(path)
        return path

    async def _apply_suggestion(
        self, path: LearningPath, suggestion: LearningPathSuggestion, user_id: UUID
    ) -> None:
        payload = suggestion.payload
        if suggestion.suggestion_type in ("add_node", "add_branch"):
            raw_nodes = payload.get("nodes", [payload.get("node")])
            new_ids: dict[str, UUID] = {}
            for raw in (item for item in raw_nodes if item):
                concept_id = UUID(raw["concept_id"]) if raw.get("concept_id") else None
                if raw.get("node_type", "concept") == NodeType.CONCEPT.value:
                    await self._validate_concept(path, user_id, concept_id)
                node_id = UUID(raw["id"]) if raw.get("id") else uuid4()
                if raw.get("temp_id"):
                    new_ids[raw["temp_id"]] = node_id
                self.repository.add(
                    LearningPathNode(
                        id=node_id,
                        learning_path_id=path.id,
                        concept_id=concept_id,
                        node_type=raw.get("node_type", "concept"),
                        title=raw["title"],
                        description=raw.get("description"),
                        position_x=raw.get("position_x"),
                        position_y=raw.get("position_y"),
                        status=raw.get("status", "planned"),
                        importance=raw.get("importance", "recommended"),
                        estimated_minutes=raw.get("estimated_minutes", 15),
                        completion_policy=raw.get("completion_policy", {}),
                        node_metadata=raw.get("metadata", {}),
                    )
                )
            await self.repository.flush()
            for raw in payload.get("edges", []):
                source = new_ids.get(raw["source"])
                target = new_ids.get(raw["target"])
                source = source or UUID(raw["source"])
                target = target or UUID(raw["target"])
                self.repository.add(
                    LearningPathEdge(
                        id=uuid4(),
                        learning_path_id=path.id,
                        source_node_id=source,
                        target_node_id=target,
                        edge_type=raw.get("edge_type", "remediation"),
                        label=raw.get("label"),
                    )
                )
        elif suggestion.suggestion_type == "reorder":
            for position in payload.get("positions", []):
                node = await self._require_node(path.id, UUID(position["node_id"]))
                node.position_x = position.get("position_x")
                node.position_y = position.get("position_y")
        elif suggestion.suggestion_type == "attach_resource":
            raw = payload["resource"]
            await self._require_node(path.id, UUID(payload["node_id"]))
            resource_id = UUID(raw["resource_id"]) if raw.get("resource_id") else None
            if raw["resource_type"] == "material" and (
                resource_id is None or not await self.repository.owns_material(user_id, resource_id)
            ):
                raise ApiError("material_not_found", "Material was not found", status_code=404)
            self.repository.add(
                LearningPathNodeResource(
                    id=uuid4(),
                    node_id=UUID(payload["node_id"]),
                    resource_type=raw["resource_type"],
                    resource_id=resource_id,
                    title=raw["title"],
                    is_required=raw.get("is_required", False),
                    order_index=raw.get("order_index", 0),
                    completion_status="planned",
                    resource_metadata=raw.get("metadata", {}),
                )
            )
        elif suggestion.suggestion_type in ("mark_blocked", "skip_node"):
            node = await self._require_node(path.id, UUID(payload["node_id"]))
            node.status = (
                NodeStatus.BLOCKED.value
                if suggestion.suggestion_type == "mark_blocked"
                else NodeStatus.SKIPPED.value
            )
        await self.repository.flush()
        self._assert_valid_graph(
            await self.repository.list_nodes(path.id), await self.repository.list_edges(path.id)
        )

    async def _suggest_missing_prerequisites(self, path: LearningPath, user_id: UUID) -> None:
        if path.status != PathStatus.ACTIVE.value or path.current_node_id is None:
            return
        nodes = await self.repository.list_nodes(path.id)
        current = next((node for node in nodes if node.id == path.current_node_id), None)
        if current is None or current.concept_id is None:
            return
        present_concepts = {node.concept_id for node in nodes if node.concept_id is not None}
        relations = await self.repository.list_concept_relations(user_id, path.learning_space_id)
        missing_ids = sorted(
            {
                relation.source_concept_id
                for relation in relations
                if relation.relation_type == "prerequisite_of"
                and relation.target_concept_id == current.concept_id
                and relation.source_concept_id not in present_concepts
            },
            key=str,
        )
        if not missing_ids:
            return
        concepts = {
            concept.id: concept
            for concept in await self.repository.list_concepts(user_id, path.learning_space_id)
        }
        states = await self.repository.get_states(missing_ids)
        pending = await self.repository.list_suggestions(path.id, pending_only=True)
        pending_keys = {
            (item.payload.get("remediation_for"), item.payload.get("concept_id"))
            for item in pending
        }
        for concept_id in missing_ids:
            state = states.get(concept_id)
            strength = min(
                state.explanation if state else 0,
                state.application if state else 0,
                state.stability if state else 0,
            )
            key = (str(current.id), str(concept_id))
            concept = concepts.get(concept_id)
            if strength >= 70 or concept is None or key in pending_keys:
                continue
            temp_id = f"remediation-{concept_id}"
            suggestion = LearningPathSuggestion(
                id=uuid4(),
                learning_path_id=path.id,
                suggestion_type="add_branch",
                payload={
                    "base_version": path.version,
                    "remediation_for": str(current.id),
                    "concept_id": str(concept_id),
                    "nodes": [
                        {
                            "temp_id": temp_id,
                            "concept_id": str(concept_id),
                            "node_type": "concept",
                            "title": concept.title,
                            "description": concept.description,
                            "importance": "recommended",
                            "estimated_minutes": 15,
                            "status": "planned",
                            "position_x": (current.position_x or 0) - 180,
                            "position_y": (current.position_y or 0) + 180,
                            "completion_policy": {},
                            "metadata": {"system_reason": "weak_missing_prerequisite"},
                        }
                    ],
                    "edges": [
                        {
                            "source": temp_id,
                            "target": str(current.id),
                            "edge_type": "remediation",
                            "label": "закрыть prerequisite gap",
                        },
                        {
                            "source": temp_id,
                            "target": str(current.id),
                            "edge_type": "returns_to",
                            "label": "вернуться к текущему узлу",
                        },
                    ],
                },
                rationale=(
                    f"Перед «{current.title}» обнаружена слабая prerequisite «{concept.title}» "
                    f"(сила {strength:.0f}/100). Добавление требует вашего подтверждения."
                ),
                source="knowledge_state",
                status=SuggestionStatus.PENDING.value,
            )
            self.repository.add(suggestion)
            self.repository.add(
                self._event(
                    "learning_path.suggestion_created",
                    path.id,
                    user_id,
                    {"suggestion_id": str(suggestion.id), "reason": "missing_prerequisite"},
                )
            )

    async def _finish_structure_change(
        self, path: LearningPath, user_id: UUID, summary: str, source: str
    ) -> None:
        path.version += 1
        await self.repository.flush()
        if path.status == PathStatus.ACTIVE.value or summary == "Learning path published":
            snapshot = await self._snapshot(path)
            self.repository.add(
                LearningPathVersion(
                    id=uuid4(),
                    learning_path_id=path.id,
                    version=path.version,
                    snapshot=snapshot,
                    change_summary=summary,
                    change_source=source,
                )
            )
            self.repository.add(
                self._event(
                    "learning_path.version_created",
                    path.id,
                    user_id,
                    {"version": path.version},
                )
            )

    async def _snapshot(self, path: LearningPath) -> dict[str, Any]:
        nodes = await self.repository.list_nodes(path.id)
        edges = await self.repository.list_edges(path.id)
        resources = await self.repository.list_resources(path.id)
        return {
            "path": {
                "title": path.title,
                "description": path.description,
                "status": path.status,
            },
            "current_node_id": str(path.current_node_id) if path.current_node_id else None,
            "nodes": [
                {
                    "id": str(item.id),
                    "concept_id": str(item.concept_id) if item.concept_id else None,
                    "node_type": item.node_type,
                    "title": item.title,
                    "description": item.description,
                    "position_x": item.position_x,
                    "position_y": item.position_y,
                    "status": item.status,
                    "importance": item.importance,
                    "estimated_minutes": item.estimated_minutes,
                    "completion_policy": item.completion_policy,
                    "metadata": item.node_metadata,
                }
                for item in nodes
            ],
            "edges": [
                {
                    "id": str(item.id),
                    "source_node_id": str(item.source_node_id),
                    "target_node_id": str(item.target_node_id),
                    "edge_type": item.edge_type,
                    "condition": item.condition,
                    "label": item.label,
                }
                for item in edges
            ],
            "resources": [
                {
                    "id": str(item.id),
                    "node_id": str(item.node_id),
                    "resource_type": item.resource_type,
                    "resource_id": str(item.resource_id) if item.resource_id else None,
                    "title": item.title,
                    "is_required": item.is_required,
                    "order_index": item.order_index,
                    "completion_status": item.completion_status,
                    "metadata": item.resource_metadata,
                }
                for item in resources
            ],
        }

    async def _advance(
        self,
        path: LearningPath,
        nodes: list[LearningPathNode],
        edges: list[LearningPathEdge],
        user_id: UUID,
    ) -> None:
        completed = {
            node.id
            for node in nodes
            if node.status in (NodeStatus.COMPLETED.value, NodeStatus.SKIPPED.value)
        }
        available = available_nodes(
            {node.id for node in nodes}, self._graph_edges(edges), completed
        )
        candidates = [node for node in nodes if node.id in available]
        candidates.sort(
            key=lambda node: (
                {"required": 0, "recommended": 1, "optional": 2}[node.importance],
                node.position_x if node.position_x is not None else 10_000,
                node.position_y if node.position_y is not None else 10_000,
                str(node.id),
            )
        )
        current = candidates[0] if candidates else None
        for node in nodes:
            if node.id in completed:
                continue
            node.status = (
                NodeStatus.CURRENT.value
                if current and node.id == current.id
                else NodeStatus.AVAILABLE.value
                if node.id in available
                else NodeStatus.BLOCKED.value
            )
        previous = path.current_node_id
        path.current_node_id = current.id if current else None
        if current is None and all(
            node.status in (NodeStatus.COMPLETED.value, NodeStatus.SKIPPED.value) for node in nodes
        ):
            path.status = PathStatus.COMPLETED.value
        elif current and current.id != previous:
            self.repository.add(
                self._event(
                    "learning_path.node_started",
                    path.id,
                    user_id,
                    {"node_id": str(current.id)},
                )
            )

    @staticmethod
    def _assert_valid_graph(nodes: list[LearningPathNode], edges: list[LearningPathEdge]) -> None:
        try:
            assert_acyclic({node.id for node in nodes}, LearningPathService._graph_edges(edges))
        except ValueError as error:
            raise ApiError(
                "invalid_learning_path_graph",
                "Learning path graph must be acyclic and stay inside one path",
                status_code=409,
                details={"reason": str(error)},
            ) from error

    @staticmethod
    def _graph_edges(edges: list[LearningPathEdge]) -> list[GraphEdge]:
        return [
            GraphEdge(edge.source_node_id, edge.target_node_id, edge.edge_type) for edge in edges
        ]

    async def _validate_concept(
        self, path: LearningPath, user_id: UUID, concept_id: UUID | None
    ) -> None:
        if concept_id is None:
            raise ApiError(
                "concept_node_requires_concept",
                "Concept node requires concept_id",
                status_code=422,
            )
        concepts = await self.repository.list_concepts(user_id, path.learning_space_id)
        if concept_id not in {concept.id for concept in concepts}:
            raise ApiError("concept_not_found", "Concept was not found", status_code=404)

    async def _require_path(self, user_id: UUID, path_id: UUID) -> LearningPath:
        path = await self.repository.get_path(user_id, path_id)
        if path is None:
            raise ApiError(
                "learning_path_not_found", "Learning path was not found", status_code=404
            )
        return path

    async def _locked_path(
        self, user_id: UUID, path_id: UUID, expected_version: int
    ) -> LearningPath:
        path = await self.repository.get_path(user_id, path_id, lock=True)
        if path is None:
            raise ApiError(
                "learning_path_not_found", "Learning path was not found", status_code=404
            )
        if path.version != expected_version:
            raise ApiError(
                "learning_path_version_conflict",
                "Learning path changed since it was loaded",
                status_code=409,
                details={"expected_version": expected_version, "actual_version": path.version},
            )
        return path

    async def _require_node(self, path_id: UUID, node_id: UUID) -> LearningPathNode:
        node = await self.repository.get_node(path_id, node_id)
        if node is None:
            raise ApiError(
                "learning_path_node_not_found", "Path node was not found", status_code=404
            )
        return node

    @staticmethod
    def _dimensions(state: Any) -> dict[str, float]:
        if state is None:
            return {}
        return {
            "recall": state.recall,
            "explanation": state.explanation,
            "structure": state.structure,
            "comparison": state.comparison,
            "application": state.application,
            "hypothesis_generation": state.hypothesis_generation,
            "stability": state.stability,
        }

    @staticmethod
    def _value(value: Any) -> Any:
        return value.value if hasattr(value, "value") else value

    @staticmethod
    def _event(
        event_type: str,
        path_id: UUID,
        user_id: UUID,
        payload: dict[str, Any] | None = None,
    ) -> OutboxEvent:
        return OutboxEvent(
            event_type=event_type,
            aggregate_type="learning_path",
            aggregate_id=str(path_id),
            payload={"user_id": str(user_id), **(payload or {})},
        )
