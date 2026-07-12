from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.modules.scheduler.domain import (
    ActiveContext,
    ActiveSessionInput,
    CalendarItemType,
    DueReviewInput,
    LowConceptInput,
    OpenGapInput,
    SchedulerCandidate,
    SchedulerInputs,
    build_candidates,
    select_daily_actions,
)

NOW = datetime(2026, 7, 12, 9, tzinfo=UTC)
SPACE_ID = uuid4()


def make_inputs() -> SchedulerInputs:
    return SchedulerInputs(
        context=ActiveContext(SPACE_ID, "Linear algebra", uuid4(), "Understand transforms"),
        due_reviews=(
            DueReviewInput(
                uuid4(),
                uuid4(),
                SPACE_ID,
                "Eigenvector",
                "explain",
                "Explain eigenvectors",
                NOW - timedelta(days=2),
            ),
        ),
        active_sessions=(ActiveSessionInput(uuid4(), uuid4(), SPACE_ID, "Matrix article", 20),),
        low_concepts=(LowConceptInput(uuid4(), SPACE_ID, "Basis", 20, 25, True),),
        open_gaps=(OpenGapInput(uuid4(), SPACE_ID, None, "Why is the kernel important?", "gap"),),
    )


def test_priority_order_matches_documented_heuristic() -> None:
    selected = select_daily_actions(build_candidates(make_inputs(), NOW), 90)

    assert [item.item_type.value for item in selected[:4]] == [
        "review",
        "gap_work",
        "material_session",
        "explain",
    ]
    assert "2" in selected[0].rationale


def test_daily_plan_never_exceeds_budget_or_item_limit() -> None:
    candidates = build_candidates(make_inputs(), NOW)

    selected = select_daily_actions(candidates, available_minutes=45, limit=3)

    assert len(selected) <= 3
    assert sum(item.estimated_minutes for item in selected) <= 45


def test_scheduler_is_deterministic_for_same_inputs() -> None:
    candidates = build_candidates(make_inputs(), NOW)

    first = select_daily_actions(candidates, 45)
    second = select_daily_actions(list(reversed(candidates)), 45)

    assert first == second


def test_action_that_does_not_fit_is_not_carried_as_debt() -> None:
    candidate = SchedulerCandidate(
        item_type=CalendarItemType.PRACTICE,
        source_type="concept",
        source_id=uuid4(),
        learning_space_id=SPACE_ID,
        title="Long practice",
        estimated_minutes=30,
        priority=999,
        rationale="Longer than the available slot",
        action_url="/concepts/example",
        target_dimension="application",
    )

    assert select_daily_actions([candidate], 15) == []


def test_prerequisite_gap_outranks_regular_low_concept() -> None:
    prerequisite = LowConceptInput(uuid4(), SPACE_ID, "Vectors", 10, 10, True)
    regular = LowConceptInput(uuid4(), SPACE_ID, "Determinant", 10, 10, False)
    inputs = SchedulerInputs(low_concepts=(regular, prerequisite))

    selected = select_daily_actions(build_candidates(inputs, NOW), 30)

    assert selected[0].source_id == prerequisite.id
    assert "prerequisite" in selected[0].rationale
