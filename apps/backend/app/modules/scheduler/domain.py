from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID


class CalendarItemType(StrEnum):
    MATERIAL_SESSION = "material_session"
    REVIEW = "review"
    EXPLAIN = "explain"
    PRACTICE = "practice"
    GAP_WORK = "gap_work"


class CalendarItemStatus(StrEnum):
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class CalendarFlexibility(StrEnum):
    FIXED = "fixed"
    FLEXIBLE = "flexible"


@dataclass(frozen=True)
class ActiveContext:
    space_id: UUID | None = None
    space_title: str | None = None
    goal_id: UUID | None = None
    goal_title: str | None = None


@dataclass(frozen=True)
class SchedulerCandidate:
    item_type: CalendarItemType
    source_type: str
    source_id: UUID | None
    learning_space_id: UUID | None
    title: str
    estimated_minutes: int
    priority: int
    rationale: str
    action_url: str
    target_dimension: str

    @property
    def key(self) -> tuple[str, UUID | None, CalendarItemType]:
        return self.source_type, self.source_id, self.item_type


@dataclass(frozen=True)
class DueReviewInput:
    id: UUID
    concept_id: UUID
    learning_space_id: UUID
    concept_title: str
    review_type: str
    prompt: str
    due_at: datetime


@dataclass(frozen=True)
class ActiveSessionInput:
    id: UUID
    material_id: UUID
    learning_space_id: UUID
    material_title: str
    estimated_minutes: int | None


@dataclass(frozen=True)
class LowConceptInput:
    id: UUID
    learning_space_id: UUID
    title: str
    explanation: float
    application: float
    is_prerequisite: bool


@dataclass(frozen=True)
class OpenGapInput:
    id: UUID
    learning_space_id: UUID
    material_id: UUID | None
    body: str
    note_type: str


@dataclass(frozen=True)
class MaterialInput:
    id: UUID
    learning_space_id: UUID
    title: str
    estimated_minutes: int | None


@dataclass(frozen=True)
class PathResourceInput:
    path_id: UUID
    path_title: str
    node_id: UUID
    node_title: str
    node_status: str
    concept_id: UUID | None
    learning_space_id: UUID
    resource_id: UUID
    resource_type: str
    source_id: UUID | None
    resource_title: str
    estimated_minutes: int


@dataclass(frozen=True)
class SchedulerInputs:
    context: ActiveContext = field(default_factory=ActiveContext)
    due_reviews: tuple[DueReviewInput, ...] = ()
    active_sessions: tuple[ActiveSessionInput, ...] = ()
    low_concepts: tuple[LowConceptInput, ...] = ()
    open_gaps: tuple[OpenGapInput, ...] = ()
    materials: tuple[MaterialInput, ...] = ()
    path_resources: tuple[PathResourceInput, ...] = ()
    average_stability: float = 0
    average_confidence: float = 0
    state_count: int = 0


def select_daily_actions(
    candidates: list[SchedulerCandidate], available_minutes: int, limit: int = 5
) -> list[SchedulerCandidate]:
    """Choose a bounded, deterministic plan that never exceeds the time budget."""
    selected: list[SchedulerCandidate] = []
    seen: set[tuple[str, UUID | None, CalendarItemType]] = set()
    remaining = available_minutes
    for candidate in sorted(
        candidates,
        key=lambda item: (-item.priority, item.estimated_minutes, item.title, str(item.source_id)),
    ):
        if candidate.key in seen or candidate.estimated_minutes > remaining:
            continue
        selected.append(candidate)
        seen.add(candidate.key)
        remaining -= candidate.estimated_minutes
        if len(selected) >= limit or remaining <= 0:
            break
    return selected


def build_candidates(inputs: SchedulerInputs, now: datetime) -> list[SchedulerCandidate]:
    candidates: list[SchedulerCandidate] = []
    review_dimensions = {
        "recall": "воспроизведение",
        "explain": "объяснение",
        "compare": "сравнение",
        "apply": "применение",
        "structure": "структуру",
    }
    for review in inputs.due_reviews:
        overdue_days = max(0, (now - review.due_at).days)
        overdue_hours = max(0, int((now - review.due_at).total_seconds() // 3600))
        candidates.append(
            SchedulerCandidate(
                item_type=CalendarItemType.REVIEW,
                source_type="review_item",
                source_id=review.id,
                learning_space_id=review.learning_space_id,
                title=f"Повторить: {review.concept_title}",
                estimated_minutes=10,
                priority=1000 + min(overdue_hours, 720),
                rationale=(
                    f"Повторение просрочено на {overdue_days} дн."
                    if overdue_days
                    else "Срок повторения наступил: извлечение из памяти укрепит след знания."
                ),
                action_url=f"/reviews?reviewId={review.id}",
                target_dimension=review_dimensions.get(review.review_type, "понимание"),
            )
        )
    resource_types = {
        "material": (CalendarItemType.MATERIAL_SESSION, "структуру"),
        "review_template": (CalendarItemType.REVIEW, "воспроизведение"),
        "practice": (CalendarItemType.PRACTICE, "применение"),
        "explanation": (CalendarItemType.EXPLAIN, "объяснение"),
        "project_task": (CalendarItemType.PRACTICE, "применение"),
    }
    for resource in inputs.path_resources:
        item_type, dimension = resource_types[resource.resource_type]
        action_url = (
            f"/materials/{resource.source_id}"
            if resource.resource_type == "material" and resource.source_id
            else f"/concepts/{resource.concept_id}"
            if resource.concept_id
            else f"/spaces/{resource.learning_space_id}/paths/{resource.path_id}"
        )
        candidates.append(
            SchedulerCandidate(
                item_type=item_type,
                source_type="learning_path_node_resource",
                source_id=resource.resource_id,
                learning_space_id=resource.learning_space_id,
                title=f"{resource.node_title}: {resource.resource_title}",
                estimated_minutes=resource.estimated_minutes,
                priority=980 if resource.node_status == "current" else 930,
                rationale=(
                    f"Текущий обязательный шаг пути «{resource.path_title}»."
                    if resource.node_status == "current"
                    else f"Доступный обязательный шаг пути «{resource.path_title}»."
                ),
                action_url=action_url,
                target_dimension=dimension,
            )
        )
    for gap in inputs.open_gaps:
        candidates.append(
            SchedulerCandidate(
                item_type=CalendarItemType.GAP_WORK,
                source_type="note",
                source_id=gap.id,
                learning_space_id=gap.learning_space_id,
                title=f"Разобрать: {gap.body[:90]}",
                estimated_minutes=15,
                priority=900 if gap.note_type == "gap" else 850,
                rationale=("Открытый пробел или вопрос из заметок блокирует движение дальше."),
                action_url=(
                    f"/materials/{gap.material_id}"
                    if gap.material_id
                    else f"/spaces/{gap.learning_space_id}"
                ),
                target_dimension="объяснение",
            )
        )
    for session in inputs.active_sessions:
        candidates.append(
            SchedulerCandidate(
                item_type=CalendarItemType.MATERIAL_SESSION,
                source_type="learning_session",
                source_id=session.id,
                learning_space_id=session.learning_space_id,
                title=f"Продолжить: {session.material_title}",
                estimated_minutes=min(session.estimated_minutes or 20, 30),
                priority=800,
                rationale=(
                    "Учебная сессия уже начата; продолжение снижает стоимость "
                    "переключения контекста."
                ),
                action_url=f"/materials/{session.material_id}",
                target_dimension="применение",
            )
        )
    for concept in inputs.low_concepts:
        target = "explanation" if concept.explanation <= concept.application else "application"
        is_prerequisite_gap = (
            concept.is_prerequisite and min(concept.explanation, concept.application) < 35
        )
        candidates.append(
            SchedulerCandidate(
                item_type=(
                    CalendarItemType.EXPLAIN
                    if target == "explanation"
                    else CalendarItemType.PRACTICE
                ),
                source_type="concept",
                source_id=concept.id,
                learning_space_id=concept.learning_space_id,
                title=(
                    f"Объяснить: {concept.title}"
                    if target == "explanation"
                    else f"Применить: {concept.title}"
                ),
                estimated_minutes=15 if target == "explanation" else 20,
                priority=780 if is_prerequisite_gap else 650,
                rationale=(
                    "Это слабый prerequisite: без него связанные концепции будут неустойчивы."
                    if is_prerequisite_gap
                    else f"Низкая грань {target}: стоит получить более сильное evidence."
                ),
                action_url=f"/concepts/{concept.id}",
                target_dimension="объяснение" if target == "explanation" else "применение",
            )
        )
    if inputs.context.goal_id and inputs.context.space_id and inputs.context.goal_title:
        candidates.append(
            SchedulerCandidate(
                item_type=CalendarItemType.PRACTICE,
                source_type="learning_goal",
                source_id=inputs.context.goal_id,
                learning_space_id=inputs.context.space_id,
                title=f"Продвинуть цель: {inputs.context.goal_title}",
                estimated_minutes=15,
                priority=450,
                rationale="Действие напрямую продвигает текущую активную цель пространства.",
                action_url=f"/spaces/{inputs.context.space_id}",
                target_dimension="применение",
            )
        )
    for material in inputs.materials[:3]:
        candidates.append(
            SchedulerCandidate(
                item_type=CalendarItemType.MATERIAL_SESSION,
                source_type="material",
                source_id=material.id,
                learning_space_id=material.learning_space_id,
                title=f"Изучить: {material.title}",
                estimated_minutes=min(material.estimated_minutes or 20, 30),
                priority=300,
                rationale=(
                    "Активный материал ещё не завершён и подходит для следующей учебной сессии."
                ),
                action_url=f"/materials/{material.id}",
                target_dimension="структуру",
            )
        )
    return candidates
