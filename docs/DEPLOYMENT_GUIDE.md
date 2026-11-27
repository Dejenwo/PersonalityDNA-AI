# Deployment guide

**Nothing is deployed.** Deployment needs the owner's authorization, accounts and budget (MASTER_PROMPT.md §4).
This guide is the runbook for the first and every later release.

## Target topology (proposed)

| Component | Proposed host | Notes |
| --- | --- | --- |
| Web | Vercel, or the web Docker image on any container platform | `NEXT_PUBLIC_*` values are fixed at build time |
| API | Container platform (Fly.io, Render, Cloud Run or AWS ECS) running `services/backend/Dockerfile` | Behind TLS; set `--forwarded-allow-ips` to the proxy; `WEB_CONCURRENCY` workers (about one per core) |
| Database | Managed PostgreSQL 16 (Supabase, Neon, RDS or Cloud SQL) with point-in-time recovery | Pooler in front once there is more than one API instance |
| Daily jobs | The API image as a scheduled one-off command | `python scripts/send_reminders.py` and `python scripts/purge_expired.py`, once a day each; both are safe to re-run |
| Secrets | The platform's secret store | Never in images, logs or the repository |
| Logs | The platform's log collector, with `PDNA_LOG_FORMAT=json` | Access logs carry route templates and request ids only |
| Uptime | An external checker on `/health/ready` and the web home page | Alert the on-call person (docs/INCIDENT_RESPONSE.md) |

## Environment

Start from `.env.example`. Set these in production; the API refuses to start if the security-critical ones are missing or unsafe:

| Setting | Production value |
| --- | --- |
| `PDNA_ENVIRONMENT` | `production` |
| `PDNA_DATABASE_URL` | The managed database, with TLS (`?sslmode=require`) |
| `PDNA_JWT_SECRET` | At least 32 random bytes |
| `PDNA_DATA_ENCRYPTION_KEY` | Base64 of 32 random bytes. Back it up separately: data encrypted with it can't be read without it |
| `PDNA_CORS_ORIGINS` | Exact `https://` web origins, no `*` |
| `PDNA_WEB_BASE_URL` | The `https://` web address used in email links |
| `PDNA_REFRESH_COOKIE_SECURE` | `true` |
| `PDNA_EMAIL_PROVIDER`, `PDNA_SMTP_*`, `PDNA_EMAIL_FROM` | A transactional email provider with SPF, DKIM and DMARC set up |
| `PDNA_RELEASE` | The release name, for example the git commit, so logs and `/health` show what is running |
| `PDNA_LOG_FORMAT` | `json` |
| `PDNA_DB_POOL_SIZE`, `PDNA_DB_MAX_OVERFLOW` | Sized so that all workers stay below the database's connection limit (docs/PERFORMANCE_TESTING.md) |
| Coach | `PDNA_COACH_PROVIDER=mock` until the owner approves the live model; then `anthropic`, `PDNA_ANTHROPIC_API_KEY` and a provider-side spending cap |
| Billing | `PDNA_BILLING_ENFORCE=false` until the owner sets up Stripe, Apple, Google and RevenueCat (docs/MONETIZATION.md) |

Web build: `NEXT_PUBLIC_API_URL`, `NEXT_PUBLIC_SITE_URL`, and for the beta `NEXT_PUBLIC_BETA=true`. Optional:
`NEXT_PUBLIC_APP_VERSION` (sent with feedback) and `NEXT_PUBLIC_SUPPORT_EMAIL` (shown on the help page).

Rate limits are kept per process. Before running more than one API instance, add a shared store (S-004, K-12).

## Release steps

1. CI is green on the release commit (backend on PostgreSQL, web, end-to-end with accessibility, secret scan).
2. Build both images and scan them for known vulnerabilities.
3. Take a database backup or note the point-in-time recovery timestamp.
4. Run `alembic upgrade head` as a one-off job with the new API image. Migrations must work with the previous
   release for one release, so a rollback never needs a downgrade.
5. Deploy the API with `PDNA_RELEASE` set; wait until `/health/ready` answers 200 on every instance.
6. Deploy the web app.
7. Run the smoke test from the API image or any machine with Python:
   `python scripts/smoke_test.py --api https://api.example.com --web https://www.example.com`.
   It is read-only and exits with 1 on any failure.
8. Take one Quick Discovery assessment by hand and read the result.
9. Watch error rates and latency for 30 minutes. To roll back, redeploy the previous images; leave the database
   as it is.
10. Record the release, its commit and the smoke-test output in the release log.

## First deployment only

- Create the first superadmin: `python scripts/grant_admin.py you@example.com superadmin` after signing up.
- Schedule the two daily jobs and check their output the next day.
- Run a restore drill (docs/DISASTER_RECOVERY.md) before inviting beta testers.
