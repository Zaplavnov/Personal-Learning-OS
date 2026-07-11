from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.dependencies import get_current_user_id
from app.db.session import get_db_session
from app.modules.concepts.application import ConceptService
from app.modules.concepts.infrastructure import SqlAlchemyConceptRepository
from app.modules.concepts.schemas import (
    ConceptCreate,
    ConceptDetailResponse,
    ConceptRelationCreate,
    ConceptRelationResponse,
    ConceptResponse,
    ConceptUpdate,
    KnowledgeGraphResponse,
)

router = APIRouter(tags=["concepts"])


def get_concept_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ConceptService:
    return ConceptService(SqlAlchemyConceptRepository(session))


CurrentUserId = Annotated[UUID, Depends(get_current_user_id)]
Service = Annotated[ConceptService, Depends(get_concept_service)]


@router.post("/concepts", response_model=ConceptResponse, status_code=status.HTTP_201_CREATED)
async def create_concept(
    payload: ConceptCreate, user_id: CurrentUserId, service: Service
) -> ConceptResponse:
    return ConceptResponse.model_validate(
        await service.create_concept(user_id, **payload.model_dump())
    )


@router.get("/concepts", response_model=list[ConceptResponse])
async def list_concepts(
    user_id: CurrentUserId,
    service: Service,
    learning_space_id: UUID | None = None,
    query: Annotated[str | None, Query(max_length=200)] = None,
) -> list[ConceptResponse]:
    concepts = await service.list_concepts(user_id, learning_space_id, query)
    return [ConceptResponse.model_validate(concept) for concept in concepts]


@router.get("/concepts/{concept_id}", response_model=ConceptDetailResponse)
async def get_concept(
    concept_id: UUID, user_id: CurrentUserId, service: Service
) -> ConceptDetailResponse:
    return ConceptDetailResponse.model_validate(await service.get_concept(user_id, concept_id))


@router.patch("/concepts/{concept_id}", response_model=ConceptResponse)
async def update_concept(
    concept_id: UUID,
    payload: ConceptUpdate,
    user_id: CurrentUserId,
    service: Service,
) -> ConceptResponse:
    concept = await service.update_concept(
        user_id, concept_id, payload.model_dump(exclude_unset=True)
    )
    return ConceptResponse.model_validate(concept)


@router.post(
    "/concept-relations",
    response_model=ConceptRelationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_concept_relation(
    payload: ConceptRelationCreate, user_id: CurrentUserId, service: Service
) -> ConceptRelationResponse:
    return ConceptRelationResponse.model_validate(
        await service.create_relation(user_id, **payload.model_dump())
    )


@router.delete("/concept-relations/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_concept_relation(
    relation_id: UUID, user_id: CurrentUserId, service: Service
) -> Response:
    await service.delete_relation(user_id, relation_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/knowledge-graph", response_model=KnowledgeGraphResponse)
async def get_knowledge_graph(
    learning_space_id: UUID, user_id: CurrentUserId, service: Service
) -> KnowledgeGraphResponse:
    concepts, relations = await service.get_graph(user_id, learning_space_id)
    return KnowledgeGraphResponse(
        concepts=[ConceptResponse.model_validate(concept) for concept in concepts],
        relations=[ConceptRelationResponse.model_validate(relation) for relation in relations],
    )
