"""A small load test for the API: concurrent virtual users repeat realistic journeys, then latency
percentiles are printed per endpoint.

    python scripts/load_test.py --base http://127.0.0.1:8000 --users 50 --seconds 60

Journeys (weights in brackets):
  assessment (3): start a Quick Discovery session, load it, save answers in batches of 5, complete,
                  read the result
  browse (1):     list assessments, languages and growth programmes

Only point it at your own local or staging API: it creates anonymous sessions, and the API's per-IP
session limit (PDNA_SESSION_CREATE_RATE_LIMIT) must be raised for the run. It sends no personal data.
"""

import argparse
import asyncio
import random
import statistics
import time
from collections import defaultdict

import httpx2 as httpx

CONSENT = {"accepted": True, "age_confirmed_18_plus": True}
rng = random.Random(7)  # noqa: S311 (reproducible test data, not security)


class Stats:
    def __init__(self) -> None:
        self.latency: dict[str, list[float]] = defaultdict(list)
        self.errors: dict[str, int] = defaultdict(int)
        self.journeys = 0

    def record(self, name: str, started: float, response: httpx.Response, ok: tuple[int, ...]) -> None:
        self.latency[name].append((time.perf_counter() - started) * 1000)
        if response.status_code not in ok:
            self.errors[f"{name} {response.status_code}"] += 1


async def call(client, stats, name, method, url, ok=(200,), **kw) -> httpx.Response:
    started = time.perf_counter()
    try:
        r = await client.request(method, url, **kw)
    except httpx.HTTPError as e:
        stats.errors[f"{name} {type(e).__name__}"] += 1
        raise
    stats.record(name, started, r, ok)
    return r


async def assessment(client: httpx.AsyncClient, stats: Stats, policy: str) -> None:
    r = await call(
        client,
        stats,
        "POST session",
        "POST",
        "/api/v1/assessment-sessions",
        ok=(201,),
        json={"instrument_id": "mini-ipip-20", "consent": {**CONSENT, "policy_version": policy}},
    )
    if r.status_code != 201:
        return
    body = r.json()
    sid, h = body["session"]["id"], {"X-Session-Token": body["resume_token"]}
    detail = await call(client, stats, "GET assessment", "GET", "/api/v1/assessments/mini-ipip-20")
    items = detail.json()["items"]
    await call(client, stats, "GET session", "GET", f"/api/v1/assessment-sessions/{sid}", headers=h)
    for i in range(0, len(items), 5):
        answers = [{"item_id": it["id"], "value": rng.randint(1, 5)} for it in items[i : i + 5]]
        await call(
            client, stats, "PUT answers", "PUT", f"/api/v1/assessment-sessions/{sid}/answers",
            json={"answers": answers}, headers=h,
        )  # fmt: skip
    done = await call(
        client, stats, "POST complete", "POST", f"/api/v1/assessment-sessions/{sid}/complete", headers=h
    )
    if done.status_code == 200:
        await call(client, stats, "GET result", "GET", f"/api/v1/results/{done.json()['id']}", headers=h)


async def browse(client: httpx.AsyncClient, stats: Stats, _policy: str) -> None:
    for name, url in [
        ("GET assessments", "/api/v1/assessments"),
        ("GET locales", "/api/v1/locales"),
        ("GET programmes", "/api/v1/growth/programs"),
    ]:
        await call(client, stats, name, "GET", url)


async def user(client, stats, policy, deadline) -> None:
    journeys = [assessment] * 3 + [browse]
    while time.perf_counter() < deadline:
        try:
            await rng.choice(journeys)(client, stats, policy)
            stats.journeys += 1
        except httpx.HTTPError:
            await asyncio.sleep(0.5)


def pct(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p / 100 * (len(ordered) - 1)))]


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--base", default="http://127.0.0.1:8000")
    ap.add_argument("--users", type=int, default=20)
    ap.add_argument("--seconds", type=int, default=30)
    ap.add_argument("--policy-version", default=None, help="defaults to the server's current version")
    args = ap.parse_args()

    limits = httpx.Limits(max_connections=args.users, max_keepalive_connections=args.users)
    async with httpx.AsyncClient(base_url=args.base, timeout=30, limits=limits) as client:
        policy = args.policy_version
        if policy is None:
            from app.security.consent import CURRENT_POLICY_VERSION

            policy = CURRENT_POLICY_VERSION
        stats = Stats()
        started = time.perf_counter()
        deadline = started + args.seconds
        await asyncio.gather(*(user(client, stats, policy, deadline) for _ in range(args.users)))
        elapsed = time.perf_counter() - started

    total = sum(len(v) for v in stats.latency.values())
    print(
        f"{args.users} users, {elapsed:.0f} s, {stats.journeys} journeys, {total} requests, "
        f"{total / elapsed:.0f} req/s"
    )
    print(f"{'endpoint':18} {'count':>7} {'p50 ms':>8} {'p95 ms':>8} {'p99 ms':>8} {'mean ms':>8}")
    for name, values in sorted(stats.latency.items()):
        print(
            f"{name:18} {len(values):7} {pct(values, 50):8.1f} {pct(values, 95):8.1f} "
            f"{pct(values, 99):8.1f} {statistics.fmean(values):8.1f}"
        )
    errors = sum(stats.errors.values())
    print(
        f"errors: {errors} ({errors / max(total, 1):.2%})"
        + "".join(f"\n  {k}: {v}" for k, v in stats.errors.items())
    )
    return 1 if errors else 0


if __name__ == "__main__":
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    raise SystemExit(asyncio.run(main()))
