from dataclasses import dataclass
from enum import StrEnum
from typing import Any
from uuid import UUID


class PathStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class NodeType(StrEnum):
    CONCEPT = "concept"
    CAPABILITY = "capability"
    MILESTONE = "milestone"


class NodeStatus(StrEnum):
    PLANNED = "planned"
    AVAILABLE = "available"
    CURRENT = "current"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class NodeImportance(StrEnum):
    REQUIRED = "required"
    RECOMMENDED = "recommended"
    OPTIONAL = "optional"


class EdgeType(StrEnum):
    SEQUENCE = "sequence"
    PREREQUISITE = "prerequisite"
    OPTIONAL_BRANCH = "optional_branch"
    REMEDIATION = "remediation"
    RETURNS_TO = "returns_to"


class ResourceType(StrEnum):
    MATERIAL = "material"
    REVIEW_TEMPLATE = "review_template"
    PRACTICE = "practice"
    EXPLANATION = "explanation"
    PROJECT_TASK = "project_task"


class ResourceStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class SuggestionType(StrEnum):
    ADD_NODE = "add_node"
    ADD_BRANCH = "add_branch"
    REORDER = "reorder"
    ATTACH_RESOURCE = "attach_resource"
    MARK_BLOCKED = "mark_blocked"
    SKIP_NODE = "skip_node"


class SuggestionSource(StrEnum):
    RULE_ENGINE = "rule_engine"
    KNOWLEDGE_STATE = "knowledge_state"
    USER = "user"
    LLM = "llm"


class SuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


STRUCTURAL_EDGE_TYPES = {
    EdgeType.SEQUENCE.value,
    EdgeType.PREREQUISITE.value,
    EdgeType.OPTIONAL_BRANCH.value,
    EdgeType.REMEDIATION.value,
}


@dataclass(frozen=True)
class GraphEdge:
    source_id: UUID
    target_id: UUID
    edge_type: str


def assert_acyclic(node_ids: set[UUID], edges: list[GraphEdge]) -> None:
    relevant = [edge for edge in edges if edge.edge_type in STRUCTURAL_EDGE_TYPES]
    adjacency: dict[UUID, list[UUID]] = {node_id: [] for node_id in node_ids}
    indegree = {node_id: 0 for node_id in node_ids}
    for edge in relevant:
        if edge.source_id == edge.target_id:
            raise ValueError("self_edge")
        if edge.source_id not in node_ids or edge.target_id not in node_ids:
            raise ValueError("foreign_node")
        adjacency[edge.source_id].append(edge.target_id)
        indegree[edge.target_id] += 1
    queue = sorted((node for node, degree in indegree.items() if degree == 0), key=str)
    visited = 0
    while queue:
        node = queue.pop(0)
        visited += 1
        for target in sorted(adjacency[node], key=str):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
                queue.sort(key=str)
    if visited != len(node_ids):
        raise ValueError("cycle")


def topological_order(node_ids: set[UUID], edges: list[GraphEdge]) -> list[UUID]:
    assert_acyclic(node_ids, edges)
    relevant = [edge for edge in edges if edge.edge_type in STRUCTURAL_EDGE_TYPES]
    indegree = {node_id: 0 for node_id in node_ids}
    adjacency: dict[UUID, list[UUID]] = {node_id: [] for node_id in node_ids}
    for edge in relevant:
        adjacency[edge.source_id].append(edge.target_id)
        indegree[edge.target_id] += 1
    queue = sorted((node for node, degree in indegree.items() if degree == 0), key=str)
    result: list[UUID] = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for target in sorted(adjacency[node], key=str):
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
                queue.sort(key=str)
    return result


def available_nodes(
    node_ids: set[UUID], edges: list[GraphEdge], completed_or_skipped: set[UUID]
) -> set[UUID]:
    incoming: dict[UUID, set[UUID]] = {node_id: set() for node_id in node_ids}
    for edge in edges:
        if edge.edge_type in STRUCTURAL_EDGE_TYPES:
            incoming[edge.target_id].add(edge.source_id)
    return {
        node_id
        for node_id in node_ids - completed_or_skipped
        if incoming[node_id].issubset(completed_or_skipped)
    }


def evaluate_completion_policy(
    policy: dict[str, Any],
    *,
    resource_counts: dict[str, int],
    dimensions: dict[str, float],
    evidence_counts: dict[str, int],
) -> tuple[bool, list[str]]:
    """Evaluate the documented MVP subset of completion conditions."""

    def evaluate(condition: dict[str, Any]) -> tuple[bool, str]:
        if "resource_type" in condition:
            resource_type = str(condition["resource_type"])
            minimum = int(condition.get("minimum_completed", 1))
            actual = resource_counts.get(resource_type, 0)
            return actual >= minimum, f"{resource_type}: {actual}/{minimum} resources completed"
        if "dimension" in condition:
            dimension = str(condition["dimension"])
            minimum = float(condition.get("minimum_score", 0))
            actual = dimensions.get(dimension, 0)
            return actual >= minimum, f"{dimension}: {actual:.0f}/{minimum:.0f}"
        if "evidence_type" in condition:
            evidence_type = str(condition["evidence_type"])
            minimum = int(condition.get("minimum_count", 1))
            actual = evidence_counts.get(evidence_type, 0)
            return actual >= minimum, f"{evidence_type}: {actual}/{minimum} evidence"
        return False, "unsupported completion condition"

    all_results = [evaluate(item) for item in policy.get("all", [])]
    any_results = [evaluate(item) for item in policy.get("any", [])]
    passed_all = all(result for result, _ in all_results)
    passed_any = not any_results or any(result for result, _ in any_results)
    reasons = [reason for passed, reason in (*all_results, *any_results) if not passed]
    passed = passed_all and passed_any
    return passed, [] if passed else reasons
