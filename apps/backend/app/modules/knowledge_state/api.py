from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.modules.knowledge_state.application import KnowledgeStateService
from app.modules.knowledge_state.infrastructure import SqlAlchemyKnowledgeStateRepository
from app.modules.knowledge_state.schemas import (
    ConceptStateDetailResponse,
    ConceptStateResponse,
    EvidenceCreate,
    EvidenceCreatedResponse,
    EvidenceResponse,
    ReviewAttemptCreate,
    ReviewAttemptResponse,
    ReviewItemCreate,
    ReviewItemResponse,
    ReviewReschedule,
    ReviewSubmittedResponse,
)

router = APIRouter(tags=["knowledge-state", "reviews"])


def get_knowledge_state_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> KnowledgeStateService:
    return KnowledgeStateService(SqlAlchemyKnowledgeStateRepository(session))


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Service = Annotated[KnowledgeStateService, Depends(get_knowledge_state_service)]


@router.get("/concepts/{concept_id}/state", response_model=ConceptStateDetailResponse)
async def get_concept_state(
    concept_id: UUID, user_id: CurrentUserId, service: Service
) -> ConceptStateDetailResponse:
    state, evidence = await service.get_state(user_id, concept_id)
    return ConceptStateDetailResponse(
        **ConceptStateResponse.model_validate(state).model_dump(),
        evidence_count=len(evidence),
        recent_evidence=[EvidenceResponse.model_validate(item) for item in reversed(evidence[-8:])],
    )


@router.post("/concepts/{concept_id}/state/recalculate", response_model=ConceptStateResponse)
async def recalculate_concept_state(
    concept_id: UUID, user_id: CurrentUserId, service: Service
) -> ConceptStateResponse:
    return ConceptStateResponse.model_validate(await service.recalculate(user_id, concept_id))


@router.get("/concepts/{concept_id}/evidence", response_model=list[EvidenceResponse])
async def list_concept_evidence(
    concept_id: UUID, user_id: CurrentUserId, service: Service
) -> list[EvidenceResponse]:
    evidence = await service.list_evidence(user_id, concept_id)
    return [EvidenceResponse.model_validate(item) for item in evidence]


@router.post(
    "/concepts/{concept_id}/evidence",
    response_model=EvidenceCreatedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_concept_evidence(
    concept_id: UUID,
    payload: EvidenceCreate,
    user_id: CurrentUserId,
    service: Service,
) -> EvidenceCreatedResponse:
    evidence, state = await service.add_manual_evidence(user_id, concept_id, **payload.model_dump())
    return EvidenceCreatedResponse(
        evidence=EvidenceResponse.model_validate(evidence),
        state=ConceptStateResponse.model_validate(state),
    )


@router.get("/reviews/due", response_model=list[ReviewItemResponse])
async def list_due_reviews(user_id: CurrentUserId, service: Service) -> list[ReviewItemResponse]:
    return [ReviewItemResponse.model_validate(item) for item in await service.due_reviews(user_id)]


@router.post(
    "/review-items",
    response_model=ReviewItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_review_item(
    payload: ReviewItemCreate, user_id: CurrentUserId, service: Service
) -> ReviewItemResponse:
    return ReviewItemResponse.model_validate(
        await service.create_review(user_id, **payload.model_dump())
    )


@router.post(
    "/review-items/{review_id}/attempts",
    response_model=ReviewSubmittedResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_review_attempt(
    review_id: UUID,
    payload: ReviewAttemptCreate,
    user_id: CurrentUserId,
    service: Service,
) -> ReviewSubmittedResponse:
    attempt, state, next_review = await service.submit_attempt(
        user_id, review_id, **payload.model_dump()
    )
    return ReviewSubmittedResponse(
        attempt=ReviewAttemptResponse.model_validate(attempt),
        state=ConceptStateResponse.model_validate(state),
        next_review=ReviewItemResponse.model_validate(next_review),
    )


@router.post("/review-items/{review_id}/skip", response_model=ReviewItemResponse)
async def skip_review(
    review_id: UUID, user_id: CurrentUserId, service: Service
) -> ReviewItemResponse:
    return ReviewItemResponse.model_validate(await service.skip_review(user_id, review_id))


@router.post("/review-items/{review_id}/reschedule", response_model=ReviewItemResponse)
async def reschedule_review(
    review_id: UUID,
    payload: ReviewReschedule,
    user_id: CurrentUserId,
    service: Service,
) -> ReviewItemResponse:
    return ReviewItemResponse.model_validate(
        await service.reschedule_review(user_id, review_id, payload.due_at)
    )
