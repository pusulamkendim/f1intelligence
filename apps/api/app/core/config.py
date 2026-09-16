from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://f1:f1@localhost:5432/f1intelligence"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: str = "http://localhost:3000"
    media_storage_backend: str = "local"
    media_storage_path: str = ".data/media"
    wikimedia_user_agent: str = Field(
        default="F1Intelligence/0.1 (development)",
        min_length=8,
    )
    source_user_agent: str = Field(
        default="F1Intelligence/0.1 (development)",
        min_length=8,
    )
    source_http_connect_timeout_seconds: float = Field(default=10.0, gt=0)
    source_http_read_timeout_seconds: float = Field(default=90.0, gt=0)
    source_http_retries: int = Field(default=3, ge=1, le=10)
    source_http_retry_backoff_seconds: float = Field(default=2.0, ge=0)
    fia_press_release_feed_url: str = "https://www.fia.com/rss/press-release"

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
