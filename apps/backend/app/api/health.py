from fastapi import APIRouter

from app.core.errors import ApiError
from app.db.health import check_database

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    try:
        await check_database()
    except Exception as exc:
        raise ApiError(
            code="database_unavailable",
            message="Database is not ready",
            status_code=503,
            details={"database": "unavailable"},
        ) from exc
    return {"status": "ready", "database": "available"}
