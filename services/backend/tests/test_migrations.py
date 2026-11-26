"""The Alembic migrations must build exactly the schema the ORM models describe."""

from alembic import command
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.database.base import Base
from app.database.session import make_engine
from app.main import create_app
from tests.conftest import CONTENT_DIR

BACKEND = CONTENT_DIR.parent / "services" / "backend"


def _config(url: str) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", url)
    return cfg


def test_upgrade_matches_models_and_downgrades(db_url):
    command.upgrade(_config(db_url), "head")
    engine = make_engine(db_url)
    with engine.connect() as conn:
        diff = compare_metadata(MigrationContext.configure(conn), Base.metadata)
    assert diff == []
    # The app runs on a migrated database (no create_all).
    settings = Settings(environment="test", database_url=db_url, content_dir=CONTENT_DIR)
    with TestClient(create_app(settings)) as c:
        assert c.get("/api/v1/assessments").status_code == 200
    command.downgrade(_config(db_url), "base")
    engine.dispose()
