from uuid import UUID

from fastapi import Request

from app.core.config import Settings


def get_current_user_id(request: Request) -> UUID:
    """Return the configured local user until authentication is introduced."""
    settings: Settings = request.app.state.settings
    return UUID(settings.local_user_id)
