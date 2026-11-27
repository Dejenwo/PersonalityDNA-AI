# Performance testing

**Status:** baseline measured in a development sandbox (Phase 23, 2026-11-27). These numbers describe one
small machine, not production. Capacity claims wait for a staging run on the real hosting.

## Targets (to confirm in staging)

| Operation | p95 target |
| --- | --- |
| GET assessment detail | < 150 ms |
| PUT answers (batch of up to 10) | < 200 ms |
| POST complete | < 400 ms |
| Web first contentful paint, mid-range phone on 4G | < 2.0 s |
| Compressed JavaScript per page | < 220 KB (enforced in CI) |
| API availability | 99.5% monthly (beta) |

## What is checked automatically

| Check | Where | What fails it |
| --- | --- | --- |
| Query budgets | `services/backend/tests/test_performance.py` | A list endpoint whose query count grows with the number of rows (N+1), or needs more than 10 queries |
| Foreign-key indexes | same file | A foreign-key column without an index (deletes and joins would scan the table) |
| Pool settings | same file | `PDNA_DB_POOL_*` settings not reaching the engine |
| Page weight | `tests/e2e/specs/perf-budget.spec.ts` | A page that loads 220 KB or more of compressed JavaScript |

## Load test

`services/backend/scripts/load_test.py` runs concurrent virtual users. Three in four repeat the assessment
journey (start a Quick Discovery session, load it, save 20 answers in batches of 5, complete, read the
result); one in four browse (assessments, languages, growth programmes). It prints p50, p95 and p99 per
endpoint and exits with 1 if any request failed. It sends no personal data. Only run it against your own
local or staging API, with the per-IP session limit raised:

```bash
PDNA_DATABASE_URL=postgresql+psycopg://... PDNA_SESSION_CREATE_RATE_LIMIT=1000000 \
  uvicorn app.main:app_factory --factory --workers 3 --port 8000
python scripts/load_test.py --base http://127.0.0.1:8000 --users 50 --seconds 60
```

### Sandbox baseline (2026-11-27)

Machine: 4 virtual CPUs shared by the API, PostgreSQL 16 and the load generator. Fresh database, default
pool settings. Times in milliseconds.

| Setup | Requests per second | Errors |
| --- | --- | --- |
| 1 worker, 1 user (service time, no queueing) | 95 | 0 |
| 1 worker, 20 users | 100 | 0 |
| 3 workers, 20 users | 305 | 0 |
| 3 workers, 50 users | 328 | 0 |

| Endpoint | 1 user p50 | 3 workers, 20 users p95 | 3 workers, 50 users p95 |
| --- | --- | --- | --- |
| GET assessment | 2.3 | 51 | 105 |
| GET session | 7.1 | 126 | 549 |
| POST session | 12.7 | 188 | 657 |
| PUT answers (5) | 13.4 | 190 | 689 |
| POST complete | 17.4 | 216 | 695 |
| GET result | 6.6 | 112 | 497 |

**Reading it.** A single request is fast (2 to 17 ms). One worker process tops out near 100 requests a
second because Python handles one request's CPU work at a time, so extra users only queue. Three workers
triple throughput. At 20 users the targets are met; at 50 users the shared machine is saturated and p95
rises to about 0.7 s, with no errors. More workers or instances, not code changes, are the next step.

## Fixes made in Phase 23

- Goals and habits lists issued one query per goal or habit (milestones, linked habits, check-ins). They now
  load in a fixed 4 and 3 queries.
- Twelve foreign-key columns had no index (migration 0017). On PostgreSQL in production, add indexes to
  large live tables with `CREATE INDEX CONCURRENTLY` instead of the plain migration.
- Connection pool size, overflow and wait are configurable; connections are recycled every 30 minutes and
  a request waits at most 10 s for one (default) instead of 30.

## Known slow paths

- `GET /api/v1/privacy/export` reads everything the person has, so it grows with their data. It is rare,
  so it stays synchronous until it becomes a problem.
- PDF reports are rendered in the request. Move them to a background worker if p95 grows.
- Rate limits are kept in each process's memory: with several workers or instances, each one counts on its
  own, so the effective limit multiplies. A shared store (Redis) is needed before horizontal scaling (S-004).

## Configuration for production

| Setting | Default | Guidance |
| --- | --- | --- |
| Uvicorn `--workers` | 1 | About one per CPU core |
| `PDNA_DB_POOL_SIZE` | 5 | Connections kept open per worker |
| `PDNA_DB_MAX_OVERFLOW` | 10 | Extra connections under bursts |
| `PDNA_DB_POOL_TIMEOUT_SECONDS` | 10 | Wait for a free connection before failing |

Keep `instances x workers x (pool size + overflow)` below PostgreSQL's `max_connections` (100 by default,
less on small managed plans), or put PgBouncer or the host's pooler in front.

## AI coach cost

The model is called only when a person sends a coach message. Per message:

| Part | Size (estimate) | Notes |
| --- | --- | --- |
| Shared instructions (`ai/prompts/coach.v1.md`) | about 1,000 tokens | Marked for prompt caching; above the model's 512-token caching minimum, so repeat calls within 5 minutes read it from cache |
| Personal context (scores, bands, archetype) | a few hundred tokens | Not cached, by design (ADR-011) |
| History | up to 20 messages (`PDNA_COACH_HISTORY_MESSAGES`) | Not cached |
| Reply | capped at 4,000 tokens (`PDNA_COACH_MAX_OUTPUT_TOKENS`) | Includes the model's thinking; effort `medium` |

At the published list price for `claude-opus-5-5` ($4 per million input tokens, $20 per million output),
a first message with about 2,000 input and 1,000 output tokens costs about $0.03, and a long conversation
near the 20-message window costs up to about $0.07 per message. The daily limit (30 messages per person by
default, `PDNA_COACH_DAILY_MESSAGE_LIMIT`) caps one person at roughly $2 a day in the worst case. These are
estimates from prompt sizes; the live evaluation run will measure real usage, which is recorded per
message in `ai_usage_records`.

**Option for the owner:** caching the conversation itself (5-minute provider cache) would cut the input
cost of follow-up messages by most of their history. It means personal context and messages sit in the
provider's short-lived cache, which the current design (ADR-011) rules out, so it is not enabled.

## Scaling plan (to be validated)

| Users | Expected changes |
| --- | --- |
| 1,000 | One API instance with 2 to 4 workers, managed PostgreSQL |
| 10,000 | 2 or more instances, shared rate limiter (Redis), connection pooler (PgBouncer) |
| 100,000 | Read replicas for history and reports, background workers for PDFs and AI, CDN for web |
| 1,000,000 | Partition responses by time, queue-based AI, regional deployment review |
