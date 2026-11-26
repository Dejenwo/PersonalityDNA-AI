from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import install_error_handlers
from app.api.v1.routes import router as v1
from app.assessments.content import load_content
from app.assessments.sync import sync_instruments
from app.core.config import Settings, get_settings
from app.database.base import Base
from app.database.session import Database
from app.security.headers import SecurityHeadersMiddleware
from app.security.rate_limit import RateLimiter


def create_app(settings: Settings | None = None, *, create_schema: bool = False) -> FastAPI:
    settings = settings or get_settings()
    content = load_content(settings.content_dir)  # fail fast on invalid content
    db = Database(settings.database_url)

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
    app.state.session_limiter = RateLimiter(settings.session_create_rate_limit)

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-Session-Token", "Authorization"],
    )
    install_error_handlers(app)
    app.include_router(v1)

    @app.get("/health", tags=["ops"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


def app_factory() -> FastAPI:
    """Entry point for uvicorn: `uvicorn app.main:app_factory --factory`."""
    return create_app()
