# Deployment guide

**Nothing is deployed.** Deployment requires the owner's authorization and accounts (MASTER_PROMPT.md §4).

## Target topology (proposed)

| Component | Proposed host | Notes |
| --- | --- | --- |
| Web | Vercel (or the web Docker image anywhere) | `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_SITE_URL` at build time |
| API | Container platform (Fly.io, Render, Cloud Run or AWS ECS) using `services/backend/Dockerfile` | Behind TLS; set `--forwarded-allow-ips` to the proxy |
| Database | Supabase Postgres | Connection pooling on |
| Daily reminders | Scheduled job on the API platform (cron, Cloud Scheduler, Fly machines) running `python scripts/send_reminders.py` once a day | Same `PDNA_*` settings as the API; safe to re-run (each reminder is sent once) |
| Data retention | Scheduled job running `python scripts/purge_expired.py` once a day | Deletes expired tokens, invitations, unfinished anonymous assessments after 30 days, notifications after 90 days and audit events after a year; safe to re-run |
| Secrets | Platform secret store | Never in images or repo |

## Release steps

1. CI green on the release commit.
2. Build images; scan them.
3. Run `alembic upgrade head` as a one-off job against the target database (backup first).
4. Deploy API, check `/health`, then deploy web.
5. Smoke test: start and complete a quick assessment.
6. Watch errors and latency for 30 minutes; roll back by redeploying the previous image (migrations must be backward compatible for one release).

## Required environment variables

See `.env.example`. In production: `PDNA_ENVIRONMENT=production`, `PDNA_DATABASE_URL`, `PDNA_CORS_ORIGINS` (exact `https://` web origins; the API refuses to start with `*` or plain HTTP), `PDNA_WEB_BASE_URL` (`https://`, used in email links). Run Uvicorn with about one worker per CPU core and size `PDNA_DB_POOL_SIZE` and `PDNA_DB_MAX_OVERFLOW` so that all workers together stay below PostgreSQL's connection limit (docs/PERFORMANCE_TESTING.md). Rate limits are per process, so add a shared store before running more than one instance. For the beta, build the web app with `NEXT_PUBLIC_BETA=true` (and optionally `NEXT_PUBLIC_APP_VERSION`) to show the beta notice and feedback link (docs/BETA_PROGRAM.md).
