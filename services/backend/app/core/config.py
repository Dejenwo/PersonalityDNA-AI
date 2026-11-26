"""Application settings. All values come from environment variables; nothing secret has a default."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[4]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDNA_", env_file=".env", extra="ignore")

    environment: str = Field(default="development", pattern="^(development|test|staging|production)$")
    database_url: str = "sqlite:///./pdna-local.db"
    content_dir: Path = REPO_ROOT / "assessment-content"
    cors_origins: list[str] = ["http://localhost:3000"]
    # Requests per minute per client IP for session creation.
    session_create_rate_limit: int = 30
    # Whether the API docs (/docs, /openapi.json) are served. Off in production by default.
    expose_docs: bool = True


@lru_cache
def get_settings() -> Settings:
    return Settings()
