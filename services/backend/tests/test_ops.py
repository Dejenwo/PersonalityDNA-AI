"""Operations: readiness, request ids, privacy-safe access logs and JSON logging."""

import json
import logging

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.ops.observability import JsonFormatter, configure_logging
from tests.conftest import CONTENT_DIR
from tests.test_auth import signup


def test_readiness_checks_the_database(client):
    r = client.get("/health/ready")
    assert r.status_code == 200 and r.json() == {"status": "ready", "release": "dev"}

    broken = create_app(
        Settings(
            environment="test",
            database_url="postgresql+psycopg://u:p@127.0.0.1:1/none",
            content_dir=CONTENT_DIR,
            db_pool_timeout_seconds=1,
            release="2026.11.27-abc123",
        )
    )
    c = TestClient(broken)  # no lifespan: startup would need the database
    assert c.get("/health").json() == {"status": "ok", "release": "2026.11.27-abc123"}
    r = c.get("/health/ready")
    assert r.status_code == 503 and r.json()["error"]["code"] == "not_ready"
    assert "u:p" not in r.text


def test_every_response_has_a_request_id_and_one_safe_log_line(client, caplog):
    logging.getLogger("pdna.access").disabled = False  # Alembic's fileConfig can disable loggers
    caplog.set_level(logging.INFO, logger="pdna.access")
    h = signup(client)
    caplog.clear()
    r = client.post(
        "/api/v1/journal/entries?secret=query-marker", json={"body": "private journal marker"}, headers=h
    )
    assert r.status_code == 201
    assert len(r.headers["x-request-id"]) == 32
    [rec] = [x for x in caplog.records if x.name == "pdna.access"]
    assert (rec.method, rec.route, rec.status) == ("POST", "/api/v1/journal/entries", 201)
    assert rec.request_id == r.headers["x-request-id"] and rec.duration_ms >= 0
    assert "marker" not in caplog.text and "query" not in caplog.text

    entry = r.json()["id"]
    caplog.clear()
    client.get(f"/api/v1/journal/entries/{entry}", headers=h)
    assert [x.route for x in caplog.records if x.name == "pdna.access"] == [
        "/api/v1/journal/entries/{entry_id}"
    ]
    assert entry not in caplog.text

    # A caller's id is reused only when it is plain; anything else is replaced.
    assert (
        client.get("/health", headers={"X-Request-ID": "lb-1234abcd"}).headers["x-request-id"]
        == "lb-1234abcd"
    )
    bad = client.get("/health", headers={"X-Request-ID": "x\ninjected log line"}).headers["x-request-id"]
    assert "injected" not in bad and len(bad) == 32
    caplog.clear()
    assert client.get("/nowhere").status_code == 404
    assert [x.route for x in caplog.records if x.name == "pdna.access"] == ["unmatched"]


def test_json_log_format():
    rec = logging.LogRecord("pdna.access", logging.INFO, __file__, 1, "request", None, None)
    rec.route, rec.status = "/health", 200
    out = json.loads(JsonFormatter("r1").format(rec))
    assert out["message"] == "request" and out["route"] == "/health" and out["status"] == 200
    assert out["release"] == "r1" and out["level"] == "INFO"

    root = logging.getLogger()
    saved, level = root.handlers[:], root.level
    try:
        configure_logging("WARNING", "json", "r2")
        assert isinstance(root.handlers[0].formatter, JsonFormatter) and root.level == logging.WARNING
        assert logging.getLogger("uvicorn.access").disabled
        configure_logging("INFO", "text", "r2")
        assert not isinstance(root.handlers[0].formatter, JsonFormatter)
    finally:
        root.handlers[:], _ = saved, root.setLevel(level)
        logging.getLogger("uvicorn.access").disabled = False


def test_smoke_test_passes_against_a_healthy_api_and_reports_failures(client, capsys):
    from scripts.smoke_test import Reply, main

    def via_client(url: str, headers: dict[str, str]) -> Reply:
        r = client.get(url.removeprefix("http://api.test"), headers=headers)
        return Reply(r.status_code, {k.lower(): v for k, v in r.headers.items()}, r.text)

    # The test app reports release "dev", which the smoke test treats as a missing release.
    client.app.state.settings.release = "dev"
    assert main(["--api", "http://api.test", "--not-production"], fetch=via_client) == 1
    out = capsys.readouterr().out
    assert "FAIL  Release is set" in out and "ok    API reaches the database" in out
    assert (
        "ok    Private endpoints need sign-in" in out and "ok    Other sites are not allowed by CORS" in out
    )
    assert out.count("FAIL") == 1

    def down(url: str, headers: dict[str, str]) -> Reply:
        raise OSError("connection refused")

    assert main(["--api", "http://api.test", "--web", "http://web.test"], fetch=down) == 1
    assert "Could not complete the checks: connection refused" in capsys.readouterr().out

    pages = {
        "/": Reply(200, {"content-security-policy": "default-src 'self'"}, "<html>"),
        "/robots.txt": Reply(200, {}, "User-Agent: *\nDisallow: /account\n"),
    }

    def web(url: str, headers: dict[str, str]) -> Reply:
        if url.startswith("http://web.test"):
            return pages.get(url.removeprefix("http://web.test"), Reply(200, {}, ""))
        return via_client(url, headers)

    from scripts import smoke_test

    report = smoke_test.Report()
    smoke_test.check_web(web, "http://web.test", report)
    assert report.failed == [] and len(report.passed) == 9
