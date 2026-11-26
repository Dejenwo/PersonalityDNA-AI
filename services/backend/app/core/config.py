"""Application settings. All values come from environment variables; nothing secret has a default."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
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

    # --- Authentication ---
    # HMAC key for access tokens. Required outside development/test (>= 32 bytes).
    jwt_secret: SecretStr | None = None
    jwt_issuer: str = "personalitydna"
    jwt_audience: str = "personalitydna-api"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_days: int = Field(default=30, ge=1, le=90)
    email_token_hours: int = Field(default=24, ge=1, le=72)
    password_reset_minutes: int = Field(default=60, ge=10, le=240)
    # Cookie for the web refresh token. Secure must be true anywhere served over HTTPS.
    refresh_cookie_secure: bool = False
    refresh_cookie_domain: str | None = None
    # Per-IP and per-email attempts per 15 minutes on login and password-reset requests.
    auth_rate_limit: int = 10
    # Base URL of the web app, used in emailed links.
    web_base_url: str = "http://localhost:3000"

    # --- Email ---
    email_provider: Literal["outbox", "smtp"] = "outbox"
    email_from: str = "PersonalityDNA <no-reply@personalitydna.local>"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: SecretStr | None = None
    # Exposes GET /api/v1/dev/outbox for local testing. Refused in staging/production.
    dev_outbox_endpoint: bool = False

    @model_validator(mode="after")
    def _production_guards(self) -> "Settings":
        if self.environment in ("staging", "production"):
            if self.jwt_secret is None or len(self.jwt_secret.get_secret_value()) < 32:
                raise ValueError("PDNA_JWT_SECRET of at least 32 characters is required outside development")
            if self.email_provider == "outbox" or self.dev_outbox_endpoint:
                raise ValueError("The development email outbox cannot be used outside development")
            if not self.refresh_cookie_secure:
                raise ValueError("PDNA_REFRESH_COOKIE_SECURE must be true outside development")
            if self.database_url.startswith("sqlite"):
                raise ValueError("SQLite is for development and tests only")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
