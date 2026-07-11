from fastapi import APIRouter, Request
from pydantic import BaseModel

from app.core.config import Settings

router = APIRouter(tags=["meta"])


class MetaResponse(BaseModel):
    name: str
    version: str
    environment: str


@router.get("/meta", response_model=MetaResponse)
async def meta(request: Request) -> MetaResponse:
    settings: Settings = request.app.state.settings
    return MetaResponse(
        name=settings.app_name,
        version=settings.app_version,
        environment=settings.app_environment,
    )
