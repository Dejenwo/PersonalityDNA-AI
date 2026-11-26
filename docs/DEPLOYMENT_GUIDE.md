# Deployment guide

**Nothing is deployed.** Deployment requires the owner's authorization and accounts (MASTER_PROMPT.md §4).

## Target topology (proposed)

| Component | Proposed host | Notes |
| --- | --- | --- |
| Web | Vercel (or the web Docker image anywhere) | `NEXT_PUBLIC_API_URL` at build time |
| API | Container platform (Fly.io, Render, Cloud Run or AWS ECS) using `services/backend/Dockerfile` | Behind TLS; set `--forwarded-allow-ips` to the proxy |
| Database | Supabase Postgres | Connection pooling on |
| Secrets | Platform secret store | Never in images or repo |

## Release steps

1. CI green on the release commit.
2. Build images; scan them.
3. Run `alembic upgrade head` as a one-off job against the target database (backup first).
4. Deploy API, check `/health`, then deploy web.
5. Smoke test: start and complete a quick assessment.
6. Watch errors and latency for 30 minutes; roll back by redeploying the previous image (migrations must be backward compatible for one release).

## Required environment variables

See `.env.example`. In production: `PDNA_ENVIRONMENT=production`, `PDNA_DATABASE_URL`, `PDNA_CORS_ORIGINS` (exact web origin).
