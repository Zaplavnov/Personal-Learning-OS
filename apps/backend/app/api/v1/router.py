from fastapi import APIRouter

from app.api.v1.meta import router as meta_router
from app.modules.concepts.api import router as concepts_router
from app.modules.learning_spaces.api import router as learning_spaces_router
from app.modules.materials.api import router as materials_router

api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(meta_router)
api_v1_router.include_router(concepts_router)
api_v1_router.include_router(learning_spaces_router)
api_v1_router.include_router(materials_router)
