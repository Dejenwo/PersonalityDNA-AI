"""The Alembic migrations must build exactly the schema the ORM models describe."""

import uuid

import sqlalchemy as sa
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


def test_0007_moves_leadership_progress_into_learning_tracks(db_url):
    cfg = _config(db_url)
    command.upgrade(cfg, "0006")
    engine = make_engine(db_url)
    user_id, row_id = uuid.uuid4(), uuid.uuid4()
    ids = (sa.bindparam("id", type_=sa.Uuid()), sa.bindparam("user", type_=sa.Uuid()))
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "INSERT INTO users (id, email, password_hash, locale, status) "
                "VALUES (:id, 'm@example.com', 'x', 'en', 'active')"
            ).bindparams(ids[0]),
            {"id": user_id},
        )
        conn.execute(
            sa.text(
                "INSERT INTO leadership_activity_progress (id, user_id, module_id, activity_id) "
                "VALUES (:id, :user, 'delegation', 'handover')"
            ).bindparams(*ids),
            {"id": row_id, "user": user_id},
        )
    command.upgrade(cfg, "0007")
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text("SELECT track, module_id, activity_id FROM learning_activity_progress")
        ).all()
    assert [tuple(r) for r in rows] == [("leadership", "delegation", "handover")]
    command.downgrade(cfg, "0006")
    with engine.connect() as conn:
        assert conn.execute(
            sa.text("SELECT module_id FROM leadership_activity_progress")
        ).scalars().all() == ["delegation"]
    command.downgrade(cfg, "base")
    engine.dispose()
