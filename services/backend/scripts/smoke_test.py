"""Read-only checks to run right after a deployment. Creates nothing and sends no personal data.

    python scripts/smoke_test.py --api https://api.example.com --web https://www.example.com

Exits with 1 if any check fails, so a deploy pipeline can roll back. Uses only the standard library, so it
runs from the API image.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field


@dataclass
class Reply:
    status: int
    headers: dict[str, str]
    body: str

    def json(self) -> object:
        return json.loads(self.body)


Fetch = Callable[[str, dict[str, str]], Reply]


def http_fetch(url: str, headers: dict[str, str]) -> Reply:
    if not url.startswith(("https://", "http://")):
        raise ValueError("Only http and https URLs")
    req = urllib.request.Request(url, headers={"User-Agent": "pdna-smoke-test", **headers})  # noqa: S310
    try:
        with urllib.request.urlopen(req, timeout=15) as r:  # noqa: S310 (scheme checked above)
            return Reply(
                r.status, {k.lower(): v for k, v in r.headers.items()}, r.read().decode("utf-8", "replace")
            )
    except urllib.error.HTTPError as e:
        return Reply(
            e.code, {k.lower(): v for k, v in e.headers.items()}, e.read().decode("utf-8", "replace")
        )


@dataclass
class Report:
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        (self.passed if ok else self.failed).append(name if ok else f"{name}: {detail}")


def check_api(fetch: Fetch, api: str, report: Report, *, production: bool) -> None:
    api = api.rstrip("/")
    live = fetch(f"{api}/health", {})
    report.check("API is up", live.status == 200, f"status {live.status}")
    ready = fetch(f"{api}/health/ready", {})
    report.check("API reaches the database", ready.status == 200, f"status {ready.status}")
    if ready.status == 200:
        release = ready.json().get("release") if isinstance(ready.json(), dict) else None  # type: ignore[union-attr]
        report.check("Release is set", bool(release) and release != "dev", f"release {release!r}")
    h = live.headers
    report.check("Responses carry a request id", bool(h.get("x-request-id")), "no X-Request-ID")
    report.check(
        "nosniff header", h.get("x-content-type-options") == "nosniff", str(h.get("x-content-type-options"))
    )
    report.check(
        "API content security policy", "default-src 'none'" in h.get("content-security-policy", ""), ""
    )
    if api.startswith("https://"):
        report.check(
            "HSTS on the API", h.get("strict-transport-security", "").startswith("max-age="), "missing"
        )
    listing = fetch(f"{api}/api/v1/assessments", {})
    items = listing.json().get("items", []) if listing.status == 200 else []  # type: ignore[union-attr]
    report.check(
        "Assessments are listed", listing.status == 200 and len(items) > 0, f"status {listing.status}"
    )
    locales = fetch(f"{api}/api/v1/locales", {})
    report.check("Languages are listed", locales.status == 200, f"status {locales.status}")
    private = fetch(f"{api}/api/v1/auth/me", {})
    report.check("Private endpoints need sign-in", private.status == 401, f"status {private.status}")
    cors = fetch(f"{api}/api/v1/assessments", {"Origin": "https://not-our-site.example"})
    report.check(
        "Other sites are not allowed by CORS",
        "access-control-allow-origin" not in cors.headers,
        str(cors.headers.get("access-control-allow-origin")),
    )
    if production:
        docs = fetch(f"{api}/docs", {})
        report.check("API explorer is hidden in production", docs.status == 404, f"status {docs.status}")


def check_web(fetch: Fetch, web: str, report: Report) -> None:
    web = web.rstrip("/")
    home = fetch(f"{web}/", {})
    report.check("Website home page loads", home.status == 200, f"status {home.status}")
    report.check(
        "Website content security policy",
        "default-src" in home.headers.get("content-security-policy", ""),
        "",
    )
    if web.startswith("https://"):
        report.check(
            "HSTS on the website", "max-age=" in home.headers.get("strict-transport-security", ""), "missing"
        )
    for path in ("/discover", "/privacy", "/help", "/feedback", "/sitemap.xml", "/robots.txt"):
        r = fetch(f"{web}{path}", {})
        report.check(f"Website {path}", r.status == 200, f"status {r.status}")
    robots = fetch(f"{web}/robots.txt", {})
    report.check("Signed-in pages are kept out of search", "Disallow: /account" in robots.body, "robots.txt")


def main(argv: list[str] | None = None, fetch: Fetch = http_fetch) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--api", required=True)
    ap.add_argument("--web")
    ap.add_argument("--not-production", action="store_true", help="skip production-only checks")
    args = ap.parse_args(argv)
    report = Report()
    try:
        check_api(fetch, args.api, report, production=not args.not_production)
        if args.web:
            check_web(fetch, args.web, report)
    except (OSError, ValueError) as exc:
        report.failed.append(f"Could not complete the checks: {exc}")
    for name in report.passed:
        print(f"ok    {name}")
    for name in report.failed:
        print(f"FAIL  {name}")
    print(f"{len(report.passed)} passed, {len(report.failed)} failed")
    return 1 if report.failed else 0


if __name__ == "__main__":
    sys.exit(main())
