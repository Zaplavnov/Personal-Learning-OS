from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.core.errors import ApiError
from app.modules.knowledge_state.domain import (
    REVIEW_DIMENSIONS,
    EvidenceType,
    KnowledgeDimension,
    ReviewResult,
    ReviewStatus,
    ReviewType,
)
from app.modules.knowledge_state.infrastructure import (
    ConceptEvidence,
    ConceptState,
    ReviewAttempt,
    ReviewItem,
    SqlAlchemyKnowledgeStateRepository,
)
from app.modules.knowledge_state.scoring import (
    EvidenceSignal,
    next_review_interval_days,
    recalculate_state,
    review_deltas,
    review_strength,
)
from app.modules.outbox.models import OutboxEvent

DEFAULT_STRENGTHS: dict[EvidenceType, float] = {
    EvidenceType.VIEWED: 0.15,
    EvidenceType.NOTE_CREATED: 0.3,
    EvidenceType.USER_EXPLANATION: 0.65,
    EvidenceType.REVIEW_ANSWER: 0.7,
    EvidenceType.TASK_SOLVED: 0.85,
    EvidenceType.APPLIED_IN_PROJECT: 1.0,
    EvidenceType.MANUAL_ADJUSTMENT: 0.5,
}


class KnowledgeStateService:
    def __init__(self, repository: SqlAlchemyKnowledgeStateRepository) -> None:
        self.repository = repository

    async def get_state(
        self, user_id: UUID, concept_id: UUID
    ) -> tuple[ConceptState, list[ConceptEvidence]]:
        await self._require_concept(user_id, concept_id)
        evidence = await self.repository.list_evidence(user_id, concept_id)
        state = await self.repository.get_state(concept_id)
        if state is None:
            state = self._state_from_evidence(concept_id, evidence, version=0)
        return state, evidence

    async def recalculate(self, user_id: UUID, concept_id: UUID) -> ConceptState:
        await self._require_concept(user_id, concept_id)
        state = await self._rebuild_state(user_id, concept_id)
        self.repository.add(self._event("knowledge_state.updated", "concept", concept_id, user_id))
        await self.repository.commit()
        return state

    async def add_manual_evidence(
        self,
        user_id: UUID,
        concept_id: UUID,
        *,
        evidence_type: EvidenceType,
        dimension: KnowledgeDimension,
        score_delta: float,
        strength: float | None,
        source_type: str,
        source_id: str | None,
        metadata: dict[str, object],
        occurred_at: datetime | None,
    ) -> tuple[ConceptEvidence, ConceptState]:
        await self._require_concept(user_id, concept_id)
        normalized_strength = self._normalize_strength(evidence_type, strength)
        evidence = ConceptEvidence(
            id=uuid4(),
            concept_id=concept_id,
            user_id=user_id,
            evidence_type=evidence_type.value,
            dimension=dimension.value,
            score_delta=score_delta,
            strength=normalized_strength,
            source_type=source_type,
            source_id=source_id,
            evidence_metadata=metadata,
            occurred_at=occurred_at or datetime.now(UTC),
        )
        self.repository.add(evidence)
        await self.repository.flush()
        state = await self._rebuild_state(user_id, concept_id)
        self.repository.add(self._event("knowledge_state.updated", "concept", concept_id, user_id))
        await self.repository.commit()
        await self.repository.refresh(evidence)
        return evidence, state

    async def list_evidence(self, user_id: UUID, concept_id: UUID) -> list[ConceptEvidence]:
        await self._require_concept(user_id, concept_id)
        return await self.repository.list_evidence(user_id, concept_id)

    async def create_review(
        self,
        user_id: UUID,
        *,
        concept_id: UUID,
        review_type: ReviewType,
        prompt: str,
        expected_points: list[str],
        due_at: datetime | None,
    ) -> ReviewItem:
        await self._require_concept(user_id, concept_id)
        review = ReviewItem(
            id=uuid4(),
            concept_id=concept_id,
            review_type=review_type.value,
            prompt=prompt,
            expected_points=expected_points,
            status=ReviewStatus.PENDING.value,
            due_at=due_at or datetime.now(UTC),
        )
        self.repository.add(review)
        await self.repository.flush()
        state = await self._ensure_state(user_id, concept_id)
        state.next_review_at = await self.repository.next_pending_review_at(concept_id)
        await self.repository.commit()
        await self.repository.refresh(review)
        return review

    async def due_reviews(self, user_id: UUID) -> list[ReviewItem]:
        return await self.repository.list_due_reviews(user_id, datetime.now(UTC))

    async def submit_attempt(
        self,
        user_id: UUID,
        review_id: UUID,
        *,
        answer: str,
        self_rating: int,
        result: ReviewResult,
        feedback: str | None,
    ) -> tuple[ReviewAttempt, ConceptState, ReviewItem]:
        review = await self.repository.get_review(user_id, review_id)
        if review is None:
            raise self._review_not_found()
        if review.status != ReviewStatus.PENDING.value:
            raise ApiError(
                "review_not_pending",
                "Review item is already resolved",
                status_code=409,
            )

        now = datetime.now(UTC)
        previous_state = await self._ensure_state(user_id, review.concept_id)
        reference_time = previous_state.last_evidence_at or review.created_at or now
        interval_days = max(0, (now - reference_time).days)
        strength = review_strength(interval_days)
        dimension = REVIEW_DIMENSIONS[ReviewType(review.review_type)]
        dimension_delta, stability_delta = review_deltas(result, self_rating)

        attempt = ReviewAttempt(
            id=uuid4(),
            review_item_id=review.id,
            answer=answer,
            self_rating=self_rating,
            result=result.value,
            feedback=feedback,
        )
        self.repository.add(attempt)
        for evidence_dimension, delta in (
            (dimension, dimension_delta),
            (KnowledgeDimension.STABILITY, stability_delta),
        ):
            self.repository.add(
                ConceptEvidence(
                    id=uuid4(),
                    concept_id=review.concept_id,
                    user_id=user_id,
                    evidence_type=EvidenceType.REVIEW_ANSWER.value,
                    dimension=evidence_dimension.value,
                    score_delta=delta,
                    strength=strength,
                    source_type="review_attempt",
                    source_id=str(attempt.id),
                    evidence_metadata={
                        "result": result.value,
                        "self_rating": self_rating,
                        "interval_days": interval_days,
                    },
                    occurred_at=now,
                )
            )
        review.status = ReviewStatus.COMPLETED.value
        await self.repository.flush()
        state = await self._rebuild_state(user_id, review.concept_id)
        due_at = now + timedelta(days=next_review_interval_days(result, state.stability))
        next_review = ReviewItem(
            id=uuid4(),
            concept_id=review.concept_id,
            review_type=review.review_type,
            prompt=review.prompt,
            expected_points=review.expected_points,
            status=ReviewStatus.PENDING.value,
            due_at=due_at,
        )
        self.repository.add(next_review)
        await self.repository.flush()
        state.next_review_at = due_at
        self.repository.add(
            self._event(
                "review.answered",
                "review_attempt",
                attempt.id,
                user_id,
                {"concept_id": str(review.concept_id), "result": result.value},
            )
        )
        self.repository.add(
            self._event("knowledge_state.updated", "concept", review.concept_id, user_id)
        )
        await self.repository.commit()
        return attempt, state, next_review

    async def skip_review(self, user_id: UUID, review_id: UUID) -> ReviewItem:
        review = await self.repository.get_review(user_id, review_id)
        if review is None:
            raise self._review_not_found()
        if review.status != ReviewStatus.PENDING.value:
            raise ApiError("review_not_pending", "Review item is already resolved", status_code=409)
        review.status = ReviewStatus.SKIPPED.value
        await self.repository.flush()
        state = await self._ensure_state(user_id, review.concept_id)
        state.next_review_at = await self.repository.next_pending_review_at(review.concept_id)
        await self.repository.commit()
        return review

    async def reschedule_review(
        self, user_id: UUID, review_id: UUID, due_at: datetime
    ) -> ReviewItem:
        review = await self.repository.get_review(user_id, review_id)
        if review is None:
            raise self._review_not_found()
        if review.status != ReviewStatus.PENDING.value:
            raise ApiError("review_not_pending", "Review item is already resolved", status_code=409)
        review.due_at = due_at
        await self.repository.flush()
        state = await self._ensure_state(user_id, review.concept_id)
        state.next_review_at = await self.repository.next_pending_review_at(review.concept_id)
        await self.repository.commit()
        return review

    async def _require_concept(self, user_id: UUID, concept_id: UUID):
        concept = await self.repository.get_concept(user_id, concept_id)
        if concept is None:
            raise ApiError("concept_not_found", "Concept was not found", status_code=404)
        return concept

    async def _ensure_state(self, user_id: UUID, concept_id: UUID) -> ConceptState:
        state = await self.repository.get_state(concept_id)
        if state is not None:
            return state
        return await self._rebuild_state(user_id, concept_id)

    async def _rebuild_state(self, user_id: UUID, concept_id: UUID) -> ConceptState:
        evidence = await self.repository.list_evidence(user_id, concept_id)
        existing = await self.repository.get_state(concept_id)
        version = (existing.version if existing else 0) + 1
        calculated = self._state_from_evidence(concept_id, evidence, version)
        if existing is None:
            self.repository.add(calculated)
            state = calculated
        else:
            for field in (
                "recall",
                "explanation",
                "structure",
                "comparison",
                "application",
                "hypothesis_generation",
                "stability",
                "confidence",
                "last_evidence_at",
                "version",
                "updated_at",
            ):
                setattr(existing, field, getattr(calculated, field))
            state = existing
        state.next_review_at = await self.repository.next_pending_review_at(concept_id)
        await self.repository.flush()
        return state

    @staticmethod
    def _state_from_evidence(
        concept_id: UUID, evidence: list[ConceptEvidence], version: int
    ) -> ConceptState:
        score = recalculate_state(
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
        return ConceptState(
            concept_id=concept_id,
            recall=score.recall,
            explanation=score.explanation,
            structure=score.structure,
            comparison=score.comparison,
            application=score.application,
            hypothesis_generation=score.hypothesis_generation,
            stability=score.stability,
            confidence=score.confidence,
            last_evidence_at=score.last_evidence_at,
            next_review_at=None,
            version=version,
            updated_at=datetime.now(UTC),
        )

    @staticmethod
    def _normalize_strength(evidence_type: EvidenceType, strength: float | None) -> float:
        value = DEFAULT_STRENGTHS[evidence_type] if strength is None else strength
        if evidence_type is EvidenceType.VIEWED:
            return min(value, 0.15)
        if evidence_type is EvidenceType.NOTE_CREATED:
            return min(value, 0.3)
        return value

    @staticmethod
    def _event(
        event_type: str,
        aggregate_type: str,
        aggregate_id: UUID,
        user_id: UUID,
        extra: dict[str, object] | None = None,
    ) -> OutboxEvent:
        return OutboxEvent(
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload={"user_id": str(user_id), **(extra or {})},
        )

    @staticmethod
    def _review_not_found() -> ApiError:
        return ApiError("review_not_found", "Review item was not found", status_code=404)
