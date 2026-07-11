from dataclasses import dataclass, replace
from datetime import datetime

from app.modules.knowledge_state.domain import KnowledgeDimension, ReviewResult


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


@dataclass(frozen=True)
class EvidenceSignal:
    evidence_id: str
    dimension: KnowledgeDimension
    score_delta: float
    strength: float
    occurred_at: datetime


@dataclass(frozen=True)
class ScoreState:
    recall: float = 0
    explanation: float = 0
    structure: float = 0
    comparison: float = 0
    application: float = 0
    hypothesis_generation: float = 0
    stability: float = 0
    confidence: float = 0
    last_evidence_at: datetime | None = None


def apply_signal(state: ScoreState, signal: EvidenceSignal) -> ScoreState:
    strength = clamp(signal.strength, 0, 1)
    current = getattr(state, signal.dimension.value)
    score = round(clamp(current + signal.score_delta * strength, 0, 100), 2)
    confidence_change = strength * (0.08 if signal.score_delta >= 0 else -0.04)
    return replace(
        state,
        **{
            signal.dimension.value: score,
            "confidence": round(clamp(state.confidence + confidence_change, 0, 1), 4),
            "last_evidence_at": signal.occurred_at,
        },
    )


def recalculate_state(evidence: list[EvidenceSignal]) -> ScoreState:
    state = ScoreState()
    for signal in sorted(evidence, key=lambda item: (item.occurred_at, item.evidence_id)):
        state = apply_signal(state, signal)
    return state


def review_strength(interval_days: int) -> float:
    """Longer retrieval intervals produce stronger evidence, capped after ~5 weeks."""
    return round(clamp(0.45 + max(interval_days, 0) / 60, 0.45, 1), 4)


def review_deltas(result: ReviewResult, self_rating: int) -> tuple[float, float]:
    rating_adjustment = (clamp(self_rating, 1, 5) - 3) * 1.5
    base, stability = {
        ReviewResult.FAILED: (-6.0, -4.0),
        ReviewResult.PARTIAL: (7.0, 3.0),
        ReviewResult.PASSED: (16.0, 10.0),
    }[result]
    return base + rating_adjustment, stability


def next_review_interval_days(result: ReviewResult, stability: float) -> int:
    """Deterministic v0: failed=1d, partial=3-7d, passed=7-27d by stability."""
    if result is ReviewResult.FAILED:
        return 1
    if result is ReviewResult.PARTIAL:
        return max(3, round(3 + clamp(stability, 0, 100) / 25))
    return max(7, round(7 + clamp(stability, 0, 100) / 5))
