"""Query budgets: list screens must not issue one query per row (N+1)."""

from sqlalchemy import event

from tests.test_auth import signup
from tests.test_security import _populate

LISTS = [
    "/api/v1/goals",
    "/api/v1/habits",
    "/api/v1/journal/entries",
    "/api/v1/journal/tags",
    "/api/v1/notifications",
    "/api/v1/reports",
    "/api/v1/share-cards",
    "/api/v1/personality/history",
    "/api/v1/relationships",
    "/api/v1/coach/conversations",
    "/api/v1/orgs",
    "/api/v1/feedback",
    "/api/v1/growth/programs",
]


def _counts(client, h) -> dict[str, int]:
    seen = {"n": 0}

    def count(*_args, **_kwargs):
        seen["n"] += 1

    engine = client.app.state.db.engine
    event.listen(engine, "before_cursor_execute", count)
    try:
        out = {}
        for path in LISTS:
            seen["n"] = 0
            assert client.get(path, headers=h).status_code == 200, path
            out[path] = seen["n"]
        return out
    finally:
        event.remove(engine, "before_cursor_execute", count)


def test_list_screens_use_a_fixed_number_of_queries(client):
    h = signup(client)
    _populate(client, h)
    once = _counts(client, h)
    _populate(client, h)
    _populate(client, h)
    assert _counts(client, h) == once
    assert max(once.values()) <= 10, once


def test_every_foreign_key_has_an_index():
    """PostgreSQL doesn't index foreign keys itself; without one, lookups and ON DELETE actions (account
    deletion) scan the whole child table."""
    from sqlalchemy import PrimaryKeyConstraint, UniqueConstraint

    from app.database.base import Base

    missing = []
    for table in Base.metadata.sorted_tables:
        leading = {next(iter(ix.columns)).name for ix in table.indexes}
        leading |= {
            next(iter(c.columns)).name
            for c in table.constraints
            if isinstance(c, PrimaryKeyConstraint | UniqueConstraint) and len(c.columns)
        }
        missing += [
            f"{table.name}.{fk.parent.name}" for fk in table.foreign_keys if fk.parent.name not in leading
        ]
    assert missing == []


def test_connection_pool_settings_reach_the_engine():
    from app.core.config import Settings
    from app.database.session import make_engine

    s = Settings(environment="test", db_pool_size=7, db_max_overflow=3, db_pool_timeout_seconds=4)
    engine = make_engine(
        "postgresql+psycopg://u:p@localhost:1/x",
        pool_size=s.db_pool_size,
        max_overflow=s.db_max_overflow,
        pool_timeout=s.db_pool_timeout_seconds,
    )
    pool = engine.pool
    assert (pool.size(), pool._max_overflow, pool._timeout, pool._recycle) == (7, 3, 4, 1800)  # type: ignore[attr-defined]
    engine.dispose()
