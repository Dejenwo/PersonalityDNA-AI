import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.assessments.content import ContentBundle, load_content
from app.core.config import REPO_ROOT, Settings
from app.main import create_app
from app.security.consent import CURRENT_POLICY_VERSION

CONTENT_DIR = REPO_ROOT / "assessment-content"
CONSENT = {"accepted": True, "age_confirmed_18_plus": True, "policy_version": CURRENT_POLICY_VERSION}


@pytest.fixture(scope="session")
def content() -> ContentBundle:
    return load_content(CONTENT_DIR)


# Set PDNA_TEST_DATABASE_URL to run the suite against PostgreSQL (CI does). Default: a fresh SQLite file.
TEST_DB_URL = os.environ.get("PDNA_TEST_DATABASE_URL")


def _reset(url: str) -> None:
    from app.database.base import Base
    from app.database.session import make_engine

    engine = make_engine(url)
    Base.metadata.drop_all(engine)
    with engine.begin() as conn:
        conn.exec_driver_sql("DROP TABLE IF EXISTS alembic_version")
    engine.dispose()


@pytest.fixture
def db_url(tmp_path: Path) -> Iterator[str]:
    if TEST_DB_URL:
        _reset(TEST_DB_URL)
        yield TEST_DB_URL
        _reset(TEST_DB_URL)
    else:
        yield f"sqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
def settings(db_url: str) -> Settings:
    return Settings(environment="test", database_url=db_url, content_dir=CONTENT_DIR)


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with TestClient(create_app(settings, create_schema=True)) as c:
        yield c


def start(client: TestClient, instrument_id: str = "mini-ipip-20") -> tuple[str, dict[str, str], dict]:
    r = client.post("/api/v1/assessment-sessions", json={"instrument_id": instrument_id, "consent": CONSENT})
    assert r.status_code == 201, r.text
    body = r.json()
    return body["session"]["id"], {"X-Session-Token": body["resume_token"]}, body
