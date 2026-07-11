from datetime import UTC, datetime, timedelta

from app.modules.knowledge_state.domain import KnowledgeDimension, ReviewResult
from app.modules.knowledge_state.scoring import (
    EvidenceSignal,
    next_review_interval_days,
    recalculate_state,
    review_deltas,
    review_strength,
)

NOW = datetime(2026, 7, 11, tzinfo=UTC)


def signal(
    evidence_id: str,
    dimension: KnowledgeDimension,
    delta: float,
    strength: float,
    days: int = 0,
) -> EvidenceSignal:
    return EvidenceSignal(evidence_id, dimension, delta, strength, NOW + timedelta(days=days))


def test_same_evidence_set_always_produces_same_state() -> None:
    evidence = [
        signal("b", KnowledgeDimension.RECALL, 20, 0.8, 1),
        signal("a", KnowledgeDimension.EXPLANATION, 10, 0.5),
    ]

    assert recalculate_state(evidence) == recalculate_state(list(reversed(evidence)))


def test_viewed_weak_signal_does_not_master_concept() -> None:
    state = recalculate_state([signal("view", KnowledgeDimension.RECALL, 2, 0.15)])

    assert state.recall == 0.3
    assert state.confidence < 0.02


def test_scores_are_clamped_without_resetting_other_dimensions() -> None:
    state = recalculate_state(
        [
            signal("high", KnowledgeDimension.APPLICATION, 200, 1),
            signal("low", KnowledgeDimension.APPLICATION, -500, 0.1, 1),
            signal("explain", KnowledgeDimension.EXPLANATION, 20, 1, 2),
        ]
    )

    assert state.application == 50
    assert state.explanation == 20


def test_failed_review_is_moderate_and_reduces_stability() -> None:
    dimension_delta, stability_delta = review_deltas(ReviewResult.FAILED, 2)

    assert -10 < dimension_delta < 0
    assert -10 < stability_delta < 0


def test_longer_interval_has_stronger_evidence() -> None:
    assert review_strength(30) > review_strength(1)
    assert review_strength(1000) == 1


def test_review_interval_is_deterministic_and_result_sensitive() -> None:
    assert next_review_interval_days(ReviewResult.FAILED, 90) == 1
    assert next_review_interval_days(ReviewResult.PARTIAL, 50) == 5
    assert next_review_interval_days(ReviewResult.PASSED, 50) == 17
