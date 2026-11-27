"""Request ids, one access log line per request, and logging setup for production.

Access logs carry only the method, the route template (``/api/v1/journal/entries/{entry_id}``, never the
real path, query string or body), the status, the duration and the request id. No IP addresses, tokens,
answers or other personal content are logged (docs/PRIVACY_REQUIREMENTS.md).
"""

import json
import logging
import re
import time
import uuid
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

ACCESS = logging.getLogger("pdna.access")
REQUEST_ID_HEADER = "x-request-id"
# A caller-supplied id is reused only if it is short and plain, so it can't inject text into logs.
_SAFE_ID = re.compile(r"^[A-Za-z0-9-]{8,64}$")


def _route_template(scope: Scope) -> str:
    route = scope.get("route")
    path = getattr(route, "path", None)
    return path if isinstance(path, str) else "unmatched"


class RequestContextMiddleware:
    """Pure ASGI middleware, so streamed responses (the coach) pass through untouched."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        incoming = dict(scope.get("headers") or []).get(REQUEST_ID_HEADER.encode(), b"").decode("latin-1")
        request_id = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        started = time.perf_counter()
        status = 500

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                headers.append((REQUEST_ID_HEADER.encode(), request_id.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            ACCESS.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": scope.get("method", ""),
                    "route": _route_template(scope),
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )


_STANDARD = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class JsonFormatter(logging.Formatter):
    """One JSON object per line, for log collectors. Adds any `extra` fields given to the logger."""

    def __init__(self, release: str) -> None:
        super().__init__()
        self.release = release

    def format(self, record: logging.LogRecord) -> str:
        out: dict[str, Any] = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "release": self.release,
        }
        out.update({k: v for k, v in record.__dict__.items() if k not in _STANDARD})
        if record.exc_info:
            out["exception"] = self.formatException(record.exc_info)
        return json.dumps(out, default=str)


def configure_logging(level: str, fmt: str, release: str) -> None:
    """Called by the production entry point only; tests and tools keep Python's defaults."""
    handler = logging.StreamHandler()
    if fmt == "json":
        handler.setFormatter(JsonFormatter(release))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)
    # Uvicorn's own access log repeats the full path with its query string; ours replaces it.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers[:] = []
        logging.getLogger(name).propagate = True
