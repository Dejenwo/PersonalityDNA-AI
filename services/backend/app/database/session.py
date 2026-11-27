from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def make_engine(url: str, *, pool_size: int = 5, max_overflow: int = 10, pool_timeout: int = 10) -> Engine:
    kwargs: dict[str, object] = {"pool_pre_ping": True}
    if url.startswith("sqlite"):
        kwargs["connect_args"] = {"check_same_thread": False}
    else:
        # Recycle before typical server and load-balancer idle timeouts close connections.
        kwargs.update(
            pool_size=pool_size, max_overflow=max_overflow, pool_timeout=pool_timeout, pool_recycle=1800
        )
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):  # type: ignore[no-untyped-def]
            dbapi_conn.execute("PRAGMA foreign_keys=ON")

    return engine


class Database:
    def __init__(
        self, url: str, *, pool_size: int = 5, max_overflow: int = 10, pool_timeout: int = 10
    ) -> None:
        self.engine = make_engine(
            url, pool_size=pool_size, max_overflow=max_overflow, pool_timeout=pool_timeout
        )
        self.sessionmaker = sessionmaker(self.engine, expire_on_commit=False)

    def session(self) -> Iterator[Session]:
        with self.sessionmaker() as s:
            yield s
