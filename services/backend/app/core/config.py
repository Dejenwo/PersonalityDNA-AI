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
    # Load draft assessment content. Defaults to on in development and test only.
    content_include_drafts: bool | None = None
    # Versioned AI prompt files (ai/prompts).
    prompts_dir: Path = REPO_ROOT / "ai" / "prompts"
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

    # --- Data protection ---
    # Base64 (url-safe) encoded 32-byte key for encrypting coaching messages at rest.
    # Required outside development/test. Generate with:
    #   python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
    data_encryption_key: SecretStr | None = None

    # --- Billing (ADR-021) ---
    # Off until the owner has set up Stripe and RevenueCat: every feature stays available.
    billing_enforce: bool = False
    stripe_secret_key: SecretStr | None = None
    stripe_webhook_secret: SecretStr | None = None
    # Plan id -> Stripe price id, e.g. {"premium-monthly": "price_123"}.
    stripe_price_ids: dict[str, str] = {}
    stripe_api_base: str = "https://api.stripe.com"
    revenuecat_webhook_auth: SecretStr | None = None
    revenuecat_api_key: SecretStr | None = None
    # Store product id -> plan id, e.g. {"pdna_premium_monthly": "premium-monthly"}.
    revenuecat_product_plans: dict[str, str] = {}
    revenuecat_api_base: str = "https://api.revenuecat.com"
    # Local checkout that grants Premium without payment. Refused in staging/production.
    billing_dev_checkout: bool = False

    # --- AI coach ---
    coach_enabled: bool = True
    # "mock" is a deterministic stand-in used in development, tests and demos. It calls no AI service.
    coach_provider: Literal["mock", "anthropic"] = "mock"
    anthropic_api_key: SecretStr | None = None
    coach_model: str = "claude-opus-5-5"
    coach_effort: Literal["low", "medium", "high"] = "medium"
    coach_max_output_tokens: int = Field(default=4000, ge=256, le=16000)
    coach_request_timeout_seconds: float = Field(default=90.0, ge=5, le=600)
    # Messages per user in any rolling 24 hours. Plans can raise this once entitlements exist.
    coach_daily_message_limit: int = Field(default=30, ge=0)
    # Previous messages of the conversation sent with each request.
    coach_history_messages: int = Field(default=20, ge=0, le=100)

    @property
    def include_drafts(self) -> bool:
        if self.content_include_drafts is not None:
            return self.content_include_drafts
        return self.environment in ("development", "test")

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
            if self.data_encryption_key is None:
                raise ValueError("PDNA_DATA_ENCRYPTION_KEY is required outside development")
            if self.content_include_drafts:
                raise ValueError("Draft assessment content cannot be enabled outside development")
            if self.billing_dev_checkout:
                raise ValueError("The development checkout cannot be used outside development")
            if self.coach_enabled and self.coach_provider == "mock":
                raise ValueError("The stand-in coach provider cannot be used outside development")
        if self.coach_provider == "anthropic" and self.anthropic_api_key is None:
            raise ValueError("PDNA_ANTHROPIC_API_KEY is required when PDNA_COACH_PROVIDER=anthropic")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
