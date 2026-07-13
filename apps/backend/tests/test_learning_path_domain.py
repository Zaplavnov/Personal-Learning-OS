from uuid import uuid4

import pytest

from app.core.errors import ApiError
from app.modules.learning_paths.application import LearningPathService
from app.modules.learning_paths.domain import (
    GraphEdge,
    assert_acyclic,
    available_nodes,
    evaluate_completion_policy,
    topological_order,
)
from app.modules.learning_paths.planner import (
    PlannerConcept,
    PlannerMaterial,
    PlannerRelation,
    PlannerState,
    RuleBasedLearningPathPlanner,
)


def test_sequence_cycle_is_rejected() -> None:
    first, second, third = uuid4(), uuid4(), uuid4()
    edges = [
        GraphEdge(first, second, "sequence"),
        GraphEdge(second, third, "prerequisite"),
        GraphEdge(third, first, "sequence"),
    ]

    with pytest.raises(ValueError, match="cycle"):
        assert_acyclic({first, second, third}, edges)


def test_returns_to_does_not_break_remediation_dag() -> None:
    current, remediation = uuid4(), uuid4()
    edges = [
        GraphEdge(remediation, current, "remediation"),
        GraphEdge(current, remediation, "returns_to"),
    ]

    assert_acyclic({current, remediation}, edges)
    assert available_nodes({current, remediation}, edges, set()) == {remediation}
    assert available_nodes({current, remediation}, edges, {remediation}) == {current}


def test_topological_order_places_prerequisites_first() -> None:
    vectors, transforms, eigenvectors = uuid4(), uuid4(), uuid4()
    edges = [
        GraphEdge(vectors, transforms, "prerequisite"),
        GraphEdge(transforms, eigenvectors, "prerequisite"),
    ]

    assert topological_order({vectors, transforms, eigenvectors}, edges) == [
        vectors,
        transforms,
        eigenvectors,
    ]


def test_completion_policy_requires_all_and_one_any_condition() -> None:
    policy = {
        "all": [
            {"resource_type": "material", "minimum_completed": 1},
            {"dimension": "explanation", "minimum_score": 60},
        ],
        "any": [
            {"dimension": "application", "minimum_score": 50},
            {"evidence_type": "task_solved", "minimum_count": 1},
        ],
    }

    passed, blockers = evaluate_completion_policy(
        policy,
        resource_counts={"material": 1},
        dimensions={"explanation": 65, "application": 20},
        evidence_counts={"task_solved": 1},
    )

    assert passed is True
    assert blockers == []


def test_viewing_material_alone_does_not_complete_policy() -> None:
    passed, blockers = evaluate_completion_policy(
        {"all": [{"dimension": "explanation", "minimum_score": 60}]},
        resource_counts={"material": 1},
        dimensions={"explanation": 15},
        evidence_counts={"viewed": 10},
    )

    assert passed is False
    assert blockers == ["explanation: 15/60"]


def test_rule_based_planner_is_deterministic_and_marks_mastered_context_optional() -> None:
    path_id = uuid4()
    prerequisite_id, target_id, material_id = uuid4(), uuid4(), uuid4()
    planner = RuleBasedLearningPathPlanner()
    arguments = {
        "path_id": path_id,
        "target_concept_ids": [target_id],
        "concepts": [
            PlannerConcept(prerequisite_id, "Vectors", None),
            PlannerConcept(target_id, "Transforms", None),
        ],
        "relations": [PlannerRelation(prerequisite_id, target_id, "prerequisite_of")],
        "states": {
            prerequisite_id: PlannerState(prerequisite_id, 90, 80, 75),
            target_id: PlannerState(target_id, 20, 10, 15),
        },
        "materials": [
            PlannerMaterial(
                material_id,
                "Visual transforms",
                20,
                {"concept_ids": [str(target_id)]},
            )
        ],
        "max_depth": 3,
    }

    first = planner.build(**arguments)
    second = planner.build(**arguments)

    assert first == second
    prerequisite = next(node for node in first.nodes if node.concept_id == prerequisite_id)
    target = next(node for node in first.nodes if node.concept_id == target_id)
    assert prerequisite.importance == "optional"
    assert prerequisite.status == "completed"
    assert target.metadata["resource_warning"] is False
    assert first.resources[0].resource_id == material_id


async def test_optimistic_version_conflict_is_explicit() -> None:
    path_id = uuid4()
    user_id = uuid4()

    class Repository:
        async def get_path(self, requested_user_id, requested_path_id, *, lock=False):
            assert lock is True
            if requested_user_id != user_id or requested_path_id != path_id:
                return None
            return type("Path", (), {"version": 4})()

    service = LearningPathService(Repository(), RuleBasedLearningPathPlanner())  # type: ignore[arg-type]

    with pytest.raises(ApiError) as caught:
        await service._locked_path(user_id, path_id, expected_version=3)

    assert caught.value.status_code == 409
    assert caught.value.code == "learning_path_version_conflict"
    assert caught.value.details == {"expected_version": 3, "actual_version": 4}


async def test_path_lookup_is_isolated_by_user() -> None:
    class Repository:
        async def get_path(self, _user_id, _path_id, *, lock=False):
            assert lock is False
            return None

    service = LearningPathService(Repository(), RuleBasedLearningPathPlanner())  # type: ignore[arg-type]

    with pytest.raises(ApiError) as caught:
        await service._require_path(uuid4(), uuid4())

    assert caught.value.status_code == 404
    assert caught.value.code == "learning_path_not_found"
