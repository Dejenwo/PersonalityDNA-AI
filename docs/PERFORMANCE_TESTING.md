# Performance testing

**Status: targets defined, not yet measured.** No scale claims are made.

## Initial SLO targets (to validate in staging)

| Operation | p95 target |
| --- | --- |
| GET assessment detail | < 150 ms |
| PUT answers (batch ≤ 10) | < 200 ms |
| POST complete | < 400 ms |
| Web first contentful paint, mid-range phone on 4G | < 2.0 s |
| API availability | 99.5% monthly (beta) |

## Load test plan

k6 scripts in `tests/performance/` simulating: start → 20 answer saves → complete → get result. Steps: 50, 200, 1,000 concurrent virtual users against staging. Watch DB connections, p95/p99, error rate.

## Scaling plan (to be validated)

| Users | Expected changes |
| --- | --- |
| 1,000 | Single API instance + managed Postgres |
| 10,000 | 2+ API instances, shared rate limiter (Redis), connection pooling (PgBouncer/Supavisor) |
| 100,000 | Read replicas for history/reports, background workers for PDFs and AI, CDN for web |
| 1,000,000 | Partition responses by time, queue-based AI, regional deployment review |
