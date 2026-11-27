from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.admin.routes import router as admin_router
from app.admin.service import AdminService
from app.api.errors import ApiError, install_error_handlers
from app.api.schemas import ErrorResponse
from app.api.v1.routes import router as v1
from app.assessments.content import load_content
from app.assessments.sync import sync_instruments
from app.auth.jwt_tokens import AccessTokenCodec
from app.auth.routes import dev_router
from app.auth.routes import router as auth_router
from app.auth.service import AuthService
from app.billing.entitlements import Entitlements
from app.billing.routes import router as billing_router
from app.billing.service import BillingService
from app.coaching.prompts import load_prompt
from app.coaching.providers import make_provider
from app.coaching.routes import router as coach_router
from app.coaching.service import CoachService
from app.core.config import Settings, get_settings
from app.database.base import Base
from app.database.session import Database
from app.feedback.routes import router as feedback_router
from app.feedback.service import FeedbackService
from app.goals.routes import router as goals_router
from app.growth.routes import router as growth_router
from app.i18n.routes import router as locales_router
from app.journal.routes import router as journal_router
from app.learning.routes import router as learning_router
from app.marketing.routes import router as marketing_router
from app.notifications.email import make_email_sender
from app.notifications.routes import router as notifications_router
from app.notifications.service import NotificationService
from app.ops.observability import RequestContextMiddleware, configure_logging
from app.organizations.routes import router as orgs_router
from app.relationships.routes import router as relationships_router
from app.reports.routes import router as reports_router
from app.security.crypto import FieldCipher
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limit import RateLimiter
from app.sharing.routes import public_router as public_card_router
from app.sharing.routes import router as share_router
from app.users.routes import router as users_router


def create_app(settings: Settings | None = None, *, create_schema: bool = False) -> FastAPI:
    settings = settings or get_settings()
    content = load_content(
        settings.content_dir, include_drafts=settings.include_drafts
    )  # fail fast on invalid content
    db = Database(
        settings.database_url,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        if create_schema:
            # Tests and throwaway local runs only. Real databases are migrated with Alembic.
            Base.metadata.create_all(db.engine)
        with db.sessionmaker() as s:
            sync_instruments(s, content)
        yield
        db.engine.dispose()

    docs = settings.expose_docs and settings.environment != "production"
    app = FastAPI(
        title="PersonalityDNA AI API",
        version="0.1.0",
        lifespan=lifespan,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.state.db = db
    app.state.content = content
    app.state.settings = settings
    app.state.session_limiter = RateLimiter(settings.session_create_rate_limit)
    app.state.auth_limiter = RateLimiter(settings.auth_rate_limit, window_seconds=15 * 60)
    app.state.access_tokens = AccessTokenCodec(settings)
    app.state.email = make_email_sender(settings)
    app.state.notifications = NotificationService(settings, app.state.email)
    app.state.auth = AuthService(settings, app.state.notifications)
    app.state.events_limiter = RateLimiter(120, window_seconds=60 * 60)
    app.state.cipher = FieldCipher.from_settings(settings)
    app.state.feedback = FeedbackService(app.state.cipher)
    # Ten messages an hour per account or, signed out, per IP address.
    app.state.feedback_limiter = RateLimiter(10, window_seconds=60 * 60)
    app.state.entitlements = Entitlements(settings)
    app.state.billing = BillingService(settings, app.state.entitlements)
    app.state.admin = AdminService(settings, app.state.entitlements)
    app.state.coach = CoachService(
        settings,
        make_provider(settings),
        app.state.cipher,
        load_prompt("coach.v1.md", settings.prompts_dir),
        db.sessionmaker,
        daily_limit=app.state.entitlements.coach_daily_messages,
    )

    app.add_middleware(SecurityHeadersMiddleware, hsts=settings.environment in ("staging", "production"))
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-Session-Token", "Authorization", "X-PDNA-CSRF"],
        expose_headers=["X-Request-ID"],
    )
    # Outermost, so every response (errors and CORS preflights included) gets a request id and a log line.
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    app.include_router(v1)
    app.include_router(auth_router)
    app.include_router(users_router)
    app.include_router(coach_router)
    app.include_router(relationships_router)
    app.include_router(learning_router)
    app.include_router(growth_router)
    app.include_router(journal_router)
    app.include_router(goals_router)
    app.include_router(reports_router)
    app.include_router(share_router)
    app.include_router(public_card_router)
    app.include_router(billing_router)
    app.include_router(admin_router)
    app.include_router(orgs_router)
    app.include_router(locales_router)
    app.include_router(notifications_router)
    app.include_router(feedback_router)
    app.include_router(marketing_router)
    if settings.dev_outbox_endpoint and settings.environment in ("development", "test"):
        app.include_router(dev_router)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        """Liveness: the process is up. Cheap; doesn't touch the database."""
        return {"status": "ok", "release": settings.release}

    @app.get("/health/ready", tags=["ops"], responses={503: {"model": ErrorResponse}})
    def ready() -> dict[str, str]:
        """Readiness: the database answers. Load balancers send traffic only while this is 200."""
        try:
            with db.engine.connect() as conn:
                conn.execute(text("select 1"))
        except Exception as exc:  # any driver error means not ready
            raise ApiError(503, "not_ready", "The database is not reachable.") from exc
        return {"status": "ready", "release": settings.release}

    return app


def app_factory() -> FastAPI:
    """Entry point for uvicorn: `uvicorn app.main:app_factory --factory`."""
    settings = get_settings()
    configure_logging(settings.log_level, settings.log_format, settings.release)
    return create_app(settings)
