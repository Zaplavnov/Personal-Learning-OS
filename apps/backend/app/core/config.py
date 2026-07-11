from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    app_name: str = "Personal Learning OS API"
    app_version: str = "0.1.0"
    app_environment: str = "development"
    log_level: str = "INFO"
    database_url: str = Field(
        default="postgresql+asyncpg://plos:plos_dev@localhost:5432/plos",
        repr=False,
    )
    frontend_origin: str = "http://localhost:3000"
    local_user_id: str = "00000000-0000-4000-8000-000000000001"
    local_user_email: str = "local@personal-learning-os.test"
    local_user_display_name: str = "Local User"
    local_user_timezone: str = "Europe/Moscow"

    @property
    def is_production(self) -> bool:
        return self.app_environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
