import asyncio
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.seed_learning_spaces import SPACE_ID, seed_learning_spaces
from app.db.session import async_session_factory
from app.modules.concepts.infrastructure import Concept, ConceptRelation
from app.modules.knowledge_state.domain import KnowledgeDimension
from app.modules.knowledge_state.infrastructure import ConceptEvidence, ConceptState, ReviewItem
from app.modules.knowledge_state.scoring import EvidenceSignal, recalculate_state
from app.modules.materials.infrastructure import LearningSession, Material, Note
from app.modules.scheduler.infrastructure import CalendarItem, ScheduleVersion

logger = logging.getLogger(__name__)

MATERIAL_IDS = [UUID(f"30000000-0000-4000-8000-{index:012d}") for index in range(1, 4)]
SESSION_ID = UUID("35000000-0000-4000-8000-000000000001")
NOTE_IDS = [UUID(f"40000000-0000-4000-8000-{index:012d}") for index in range(1, 5)]
CONCEPT_IDS = [UUID(f"50000000-0000-4000-8000-{index:012d}") for index in range(1, 8)]
RELATION_IDS = [UUID(f"60000000-0000-4000-8000-{index:012d}") for index in range(1, 8)]
REVIEW_IDS = [UUID(f"80000000-0000-4000-8000-{index:012d}") for index in range(1, 3)]
CALENDAR_IDS = [UUID(f"90000000-0000-4000-8000-{index:012d}") for index in range(1, 3)]
SCHEDULE_VERSION_ID = UUID("a0000000-0000-4000-8000-000000000001")


async def seed_demo() -> None:
    await seed_learning_spaces()
    settings = get_settings()
    user_id = UUID(settings.local_user_id)
    now = datetime.now(UTC)

    async with async_session_factory() as session:
        material_specs = [
            (
                MATERIAL_IDS[0],
                "video",
                "Линейные преобразования: геометрическая интуиция",
                "https://www.youtube.com/watch?v=kYB8IZa5AuE",
                24,
            ),
            (
                MATERIAL_IDS[1],
                "article",
                "Матрица как преобразование пространства",
                "https://example.com/linear-transformations",
                18,
            ),
            (
                MATERIAL_IDS[2],
                "book",
                "Глава: собственные значения и собственные векторы",
                None,
                30,
            ),
        ]
        for material_id, material_type, title, url, minutes in material_specs:
            material = await session.get(Material, material_id)
            if material is None:
                session.add(
                    Material(
                        id=material_id,
                        user_id=user_id,
                        learning_space_id=SPACE_ID,
                        type=material_type,
                        title=title,
                        url=url,
                        description="Демонстрационный материал полного учебного цикла.",
                        status="active",
                        estimated_minutes=minutes,
                        material_metadata={"demo_seed": True},
                    )
                )
            else:
                material.title = title
                material.estimated_minutes = minutes
        await session.flush()

        learning_session = await session.get(LearningSession, SESSION_ID)
        if learning_session is None:
            learning_session = await session.scalar(
                select(LearningSession).where(
                    LearningSession.user_id == user_id,
                    LearningSession.status == "active",
                )
            )
            if learning_session is None:
                learning_session = LearningSession(
                    id=SESSION_ID,
                    material_id=MATERIAL_IDS[1],
                    user_id=user_id,
                    started_at=now - timedelta(minutes=7),
                    start_position_seconds=0,
                    status="active",
                )
                session.add(learning_session)

        note_specs = [
            (
                NOTE_IDS[0],
                MATERIAL_IDS[0],
                "insight",
                "Матрица описывает действие на базисных векторах.",
            ),
            (
                NOTE_IDS[1],
                MATERIAL_IDS[0],
                "gap",
                "Почему собственный вектор сохраняет направление?",
            ),
            (
                NOTE_IDS[2],
                MATERIAL_IDS[1],
                "question",
                "Как увидеть ядро преобразования геометрически?",
            ),
            (
                NOTE_IDS[3],
                MATERIAL_IDS[2],
                "example",
                "Растяжение вдоль осей — простой пример диагональной матрицы.",
            ),
        ]
        for note_id, material_id, note_type, body in note_specs:
            note = await session.get(Note, note_id)
            if note is None:
                session.add(
                    Note(
                        id=note_id,
                        user_id=user_id,
                        learning_space_id=SPACE_ID,
                        material_id=material_id,
                        learning_session_id=(
                            learning_session.id if material_id == MATERIAL_IDS[1] else None
                        ),
                        body=body,
                        note_type=note_type,
                    )
                )

        concept_specs = [
            (CONCEPT_IDS[0], "Вектор", "Направленная величина в линейном пространстве."),
            (
                CONCEPT_IDS[1],
                "Линейное преобразование",
                "Отображение, сохраняющее сложение и масштабирование.",
            ),
            (
                CONCEPT_IDS[2],
                "Матрица преобразования",
                "Координатная запись линейного отображения.",
            ),
            (
                CONCEPT_IDS[3],
                "Базис",
                "Система векторов для единственного представления пространства.",
            ),
            (CONCEPT_IDS[4], "Собственный вектор", "Направление, сохраняемое преобразованием."),
            (
                CONCEPT_IDS[5],
                "Собственное значение",
                "Коэффициент растяжения собственного вектора.",
            ),
            (CONCEPT_IDS[6], "Диагонализация", "Представление оператора в собственном базисе."),
        ]
        concept_by_title: dict[str, Concept] = {}
        for preferred_id, title, description in concept_specs:
            concept = await session.scalar(
                select(Concept).where(Concept.learning_space_id == SPACE_ID, Concept.title == title)
            )
            if concept is None:
                concept = Concept(
                    id=preferred_id,
                    user_id=user_id,
                    learning_space_id=SPACE_ID,
                    title=title,
                    description=description,
                    aliases=[],
                    status="active",
                )
                session.add(concept)
            else:
                concept.description = description
            concept_by_title[title] = concept
        await session.flush()

        relation_specs = [
            ("Вектор", "Линейное преобразование", "prerequisite_of"),
            ("Базис", "Матрица преобразования", "prerequisite_of"),
            ("Линейное преобразование", "Матрица преобразования", "explains"),
            ("Линейное преобразование", "Собственный вектор", "prerequisite_of"),
            ("Собственный вектор", "Собственное значение", "part_of"),
            ("Собственный вектор", "Диагонализация", "prerequisite_of"),
            ("Собственное значение", "Диагонализация", "prerequisite_of"),
        ]
        for relation_id, (source_title, target_title, relation_type) in zip(
            RELATION_IDS, relation_specs, strict=True
        ):
            source = concept_by_title[source_title]
            target = concept_by_title[target_title]
            relation = await session.scalar(
                select(ConceptRelation).where(
                    ConceptRelation.source_concept_id == source.id,
                    ConceptRelation.target_concept_id == target.id,
                    ConceptRelation.relation_type == relation_type,
                )
            )
            if relation is None:
                session.add(
                    ConceptRelation(
                        id=relation_id,
                        user_id=user_id,
                        learning_space_id=SPACE_ID,
                        source_concept_id=source.id,
                        target_concept_id=target.id,
                        relation_type=relation_type,
                    )
                )
        await session.flush()

        score_profiles = [
            (72, 55, 64),
            (52, 31, 40),
            (38, 22, 28),
            (80, 62, 70),
            (42, 18, 26),
            (48, 24, 30),
            (25, 12, 18),
        ]
        for index, ((_, title, _), (recall, explanation, application)) in enumerate(
            zip(concept_specs, score_profiles, strict=True), start=1
        ):
            concept = concept_by_title[title]
            evidence_specs = [
                (KnowledgeDimension.RECALL, recall, 0.7),
                (KnowledgeDimension.EXPLANATION, explanation, 0.8),
                (KnowledgeDimension.APPLICATION, application, 0.85),
                (KnowledgeDimension.STABILITY, min(recall, explanation), 0.65),
            ]
            for dimension_index, (dimension, delta, strength) in enumerate(evidence_specs, start=1):
                evidence_id = UUID(f"70000000-0000-4000-{index:04x}-{dimension_index:012d}")
                if await session.get(ConceptEvidence, evidence_id) is None:
                    session.add(
                        ConceptEvidence(
                            id=evidence_id,
                            concept_id=concept.id,
                            user_id=user_id,
                            evidence_type="manual_adjustment",
                            dimension=dimension.value,
                            score_delta=delta,
                            strength=strength,
                            source_type="demo_seed",
                            evidence_metadata={"profile": index},
                            occurred_at=now - timedelta(days=8 - index),
                        )
                    )
        await session.flush()

        for concept in concept_by_title.values():
            evidence = list(
                await session.scalars(
                    select(ConceptEvidence)
                    .where(ConceptEvidence.concept_id == concept.id)
                    .order_by(ConceptEvidence.occurred_at, ConceptEvidence.id)
                )
            )
            calculated = recalculate_state(
                [
                    EvidenceSignal(
                        evidence_id=str(item.id),
                        dimension=KnowledgeDimension(item.dimension),
                        score_delta=item.score_delta,
                        strength=item.strength,
                        occurred_at=item.occurred_at,
                    )
                    for item in evidence
                ]
            )
            state = await session.get(ConceptState, concept.id)
            if state is None:
                state = ConceptState(concept_id=concept.id)
                session.add(state)
            for dimension in KnowledgeDimension:
                setattr(state, dimension.value, getattr(calculated, dimension.value))
            state.confidence = calculated.confidence
            state.last_evidence_at = calculated.last_evidence_at
            state.version = max(state.version or 0, 1)
            state.updated_at = now

        review_specs = [
            (
                REVIEW_IDS[0],
                "Собственный вектор",
                "explain",
                "Объясни, почему собственный вектор сохраняет направление.",
            ),
            (
                REVIEW_IDS[1],
                "Матрица преобразования",
                "apply",
                "Приведи геометрический пример действия матрицы размером два на два.",
            ),
        ]
        for offset, (review_id, concept_title, review_type, prompt) in enumerate(review_specs):
            review = await session.get(ReviewItem, review_id)
            if review is None:
                review = ReviewItem(
                    id=review_id,
                    concept_id=concept_by_title[concept_title].id,
                    review_type=review_type,
                    prompt=prompt,
                    expected_points=[],
                    status="pending",
                    due_at=now - timedelta(hours=2 - offset),
                )
                session.add(review)
        await session.flush()

        calendar_specs = [
            (
                CALENDAR_IDS[0],
                "review",
                "review_item",
                REVIEW_IDS[0],
                "Повторить: Собственный вектор",
                10,
                1000,
                "Просроченное повторение имеет наивысший приоритет.",
            ),
            (
                CALENDAR_IDS[1],
                "material_session",
                "learning_session",
                learning_session.id,
                "Продолжить: Матрица как преобразование пространства",
                18,
                800,
                "Сессия уже начата — сохраним учебный контекст.",
            ),
        ]
        day_start = datetime.combine(now.date(), datetime.min.time(), tzinfo=UTC)
        for index, spec in enumerate(calendar_specs):
            item_id, item_type, source_type, source_id, title, minutes, priority, rationale = spec
            item = await session.get(CalendarItem, item_id)
            if item is None:
                session.add(
                    CalendarItem(
                        id=item_id,
                        user_id=user_id,
                        learning_space_id=SPACE_ID,
                        item_type=item_type,
                        source_type=source_type,
                        source_id=source_id,
                        title=title,
                        planned_start=day_start + timedelta(hours=9, minutes=index * 15),
                        estimated_minutes=minutes,
                        status="planned",
                        flexibility="flexible",
                        priority=priority,
                        rationale=rationale,
                    )
                )
        if await session.get(ScheduleVersion, SCHEDULE_VERSION_ID) is None:
            session.add(
                ScheduleVersion(
                    id=SCHEDULE_VERSION_ID,
                    user_id=user_id,
                    reason="demo_seed",
                    snapshot={
                        "available_minutes": 45,
                        "calendar_item_ids": [str(item) for item in CALENDAR_IDS],
                    },
                )
            )
        await session.commit()
    logger.info("demo_seeded", extra={"space_id": str(SPACE_ID)})


async def main() -> None:
    configure_logging(get_settings().log_level)
    await seed_demo()


if __name__ == "__main__":
    asyncio.run(main())
