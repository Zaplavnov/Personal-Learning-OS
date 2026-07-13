from dataclasses import dataclass
from typing import Any, Protocol
from uuid import UUID, uuid5

from app.modules.learning_paths.domain import GraphEdge, topological_order


@dataclass(frozen=True)
class PlannerConcept:
    id: UUID
    title: str
    description: str | None


@dataclass(frozen=True)
class PlannerRelation:
    source_id: UUID
    target_id: UUID
    relation_type: str


@dataclass(frozen=True)
class PlannerState:
    concept_id: UUID
    explanation: float
    application: float
    stability: float


@dataclass(frozen=True)
class PlannerMaterial:
    id: UUID
    title: str
    estimated_minutes: int | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PlannedNode:
    id: UUID
    concept_id: UUID
    title: str
    description: str | None
    position_x: float
    position_y: float
    status: str
    importance: str
    estimated_minutes: int | None
    completion_policy: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class PlannedEdge:
    id: UUID
    source_node_id: UUID
    target_node_id: UUID
    edge_type: str


@dataclass(frozen=True)
class PlannedResource:
    id: UUID
    node_id: UUID
    resource_type: str
    resource_id: UUID
    title: str
    is_required: bool
    order_index: int


@dataclass(frozen=True)
class DraftPlan:
    nodes: tuple[PlannedNode, ...]
    edges: tuple[PlannedEdge, ...]
    resources: tuple[PlannedResource, ...]
    rationale: str


class LearningPathPlanner(Protocol):
    def build(
        self,
        *,
        path_id: UUID,
        target_concept_ids: list[UUID],
        concepts: list[PlannerConcept],
        relations: list[PlannerRelation],
        states: dict[UUID, PlannerState],
        materials: list[PlannerMaterial],
        max_depth: int,
    ) -> DraftPlan: ...


class RuleBasedLearningPathPlanner:
    mastery_threshold = 70

    def build(
        self,
        *,
        path_id: UUID,
        target_concept_ids: list[UUID],
        concepts: list[PlannerConcept],
        relations: list[PlannerRelation],
        states: dict[UUID, PlannerState],
        materials: list[PlannerMaterial],
        max_depth: int,
    ) -> DraftPlan:
        by_id = {concept.id: concept for concept in concepts}
        prerequisite_sources: dict[UUID, list[UUID]] = {}
        for relation in relations:
            if relation.relation_type == "prerequisite_of":
                prerequisite_sources.setdefault(relation.target_id, []).append(relation.source_id)
        selected: set[UUID] = set()

        def collect(concept_id: UUID, depth: int) -> None:
            if concept_id in selected or concept_id not in by_id:
                return
            selected.add(concept_id)
            if depth >= max_depth:
                return
            for prerequisite_id in sorted(prerequisite_sources.get(concept_id, []), key=str):
                collect(prerequisite_id, depth + 1)

        for target_id in sorted(target_concept_ids, key=str):
            collect(target_id, 0)
        node_id_by_concept = {
            concept_id: uuid5(path_id, f"concept-node:{concept_id}") for concept_id in selected
        }
        graph_edges = [
            GraphEdge(source_id, target_id, "prerequisite")
            for target_id in selected
            for source_id in prerequisite_sources.get(target_id, [])
            if source_id in selected
        ]
        concept_order = topological_order(selected, graph_edges)
        depth_by_concept: dict[UUID, int] = {}
        for concept_id in concept_order:
            predecessors = [edge.source_id for edge in graph_edges if edge.target_id == concept_id]
            depth_by_concept[concept_id] = (
                max((depth_by_concept[item] for item in predecessors), default=-1) + 1
            )
        lane_by_depth: dict[int, int] = {}
        planned_nodes: list[PlannedNode] = []
        planned_resources: list[PlannedResource] = []
        for concept_id in concept_order:
            concept = by_id[concept_id]
            state = states.get(concept_id)
            already_known = bool(
                state
                and min(state.explanation, state.application, state.stability)
                >= self.mastery_threshold
            )
            depth = depth_by_concept[concept_id]
            lane = lane_by_depth.get(depth, 0)
            lane_by_depth[depth] = lane + 1
            matching_materials = [
                material
                for material in materials
                if str(concept_id) in material.metadata.get("concept_ids", [])
            ]
            node_id = node_id_by_concept[concept_id]
            planned_nodes.append(
                PlannedNode(
                    id=node_id,
                    concept_id=concept_id,
                    title=concept.title,
                    description=None,
                    position_x=depth * 300.0,
                    position_y=lane * 160.0,
                    status="completed" if already_known else "planned",
                    importance=(
                        "optional"
                        if already_known
                        else "required"
                        if concept_id in target_concept_ids
                        else "recommended"
                    ),
                    estimated_minutes=sum(
                        material.estimated_minutes or 20 for material in matching_materials
                    )
                    or 15,
                    completion_policy={
                        "all": [{"dimension": "explanation", "minimum_score": 60}],
                        "any": [
                            {"dimension": "application", "minimum_score": 50},
                            {"evidence_type": "task_solved", "minimum_count": 1},
                        ],
                    },
                    metadata={
                        "planner_rationale": (
                            "Уже освоенный prerequisite оставлен как контекст."
                            if already_known
                            else "Добавлен из prerequisite-графа."
                            if concept_id not in target_concept_ids
                            else "Целевая концепция Learning Goal."
                        ),
                        "already_known": already_known,
                        "resource_warning": not matching_materials,
                    },
                )
            )
            for index, material in enumerate(matching_materials):
                planned_resources.append(
                    PlannedResource(
                        id=uuid5(path_id, f"resource:{concept_id}:{material.id}"),
                        node_id=node_id,
                        resource_type="material",
                        resource_id=material.id,
                        title=material.title,
                        is_required=index == 0,
                        order_index=index,
                    )
                )
        planned_edges = tuple(
            PlannedEdge(
                id=uuid5(path_id, f"edge:{edge.source_id}:{edge.target_id}:prerequisite"),
                source_node_id=node_id_by_concept[edge.source_id],
                target_node_id=node_id_by_concept[edge.target_id],
                edge_type="prerequisite",
            )
            for edge in graph_edges
        )
        return DraftPlan(
            nodes=tuple(planned_nodes),
            edges=planned_edges,
            resources=tuple(planned_resources),
            rationale=(
                "Target concepts expanded through prerequisite_of relations, ordered "
                "topologically, and annotated with current Knowledge State."
            ),
        )
