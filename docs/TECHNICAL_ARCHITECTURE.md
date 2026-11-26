# Technical architecture

## Overview

```
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │ Web (Next.js)│   │ Mobile (Expo)│   │ Admin/Enter- │
 │  apps/web    │   │ apps/mobile  │   │ prise (Next) │
 └──────┬───────┘   └──────┬───────┘   └──────┬───────┘
        │  typed client (packages/api-client, generated from OpenAPI)
        └───────────────┬──┴──────────────────┘
                        ▼  HTTPS, JSON, /api/v1
           ┌─────────────────────────────────┐
           │ FastAPI modular monolith         │
           │ services/backend/app             │
           │  api · assessments · scoring ·   │
           │  personality · security · ...    │
           └──────┬─────────────┬────────────┘
                  ▼             ▼ (planned)
           PostgreSQL 16   LLM providers, Stripe, RevenueCat,
           (Supabase in    email, object storage, Sentry
            production)
```

Solid boxes for web and backend exist today. Mobile, admin and enterprise apps and all external services are planned.

## Decisions (details in ARCHITECTURE_DECISIONS.md)

- **Modular monolith** (ADR-002): one deployable backend with domain packages; split only when load or team boundaries justify it.
- **Content as versioned files** (ADR-003): instruments and scoring rules live in `assessment-content/`, are validated on startup, hashed and registered in the database; released versions are immutable.
- **Pure scoring engine** (ADR-004): no I/O, no clock, no AI; versioned with `ENGINE_VERSION`.
- **Anonymous-first sessions** (ADR-005): assessments can be taken before signup; a random resume token (stored hashed) authorizes the session. Accounts will claim sessions.
- **Contract-first client** (ADR-006): OpenAPI is exported from the backend and TypeScript types generated; CI fails on drift.
- **Auth behind an interface** (ADR-007): Supabase Auth in production, verified by JWT on the backend; a local implementation for development and tests.

## Backend

- Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, psycopg 3.
- `app/main.py:create_app` builds the app from `Settings` (environment variables `PDNA_*`). Content is loaded and validated before the app accepts traffic.
- Request flow: route (`api/v1/routes.py`) → service (`assessments/service.py`) → pure engine (`scoring/engine.py`, `personality/archetypes.py`) → presenter (`api/v1/presenters.py`).
- Errors: `ApiError` → `{"error": {"code", "message", "details"}}`.
- Cross-cutting: security headers middleware, CORS allow-list, in-process rate limiter (single instance only; see KNOWN_ISSUES).

## Web

- Next.js 16 App Router, React 19, Tailwind CSS 4, TypeScript strict.
- Assessment screens are client components because tokens live in the browser. Static pages are prerendered.
- `AnswerQueue` batches answers, keeps order, retries with backoff and surfaces save status. Tokens move between pages in the URL fragment (never sent to servers) and are stored in `localStorage`.
- Strict security headers and CSP set in `next.config.ts`.

## Data

See DATABASE_DESIGN.md. PostgreSQL in all real environments; SQLite only for fast tests.

## Environments

| Env | Database | Purpose |
| --- | --- | --- |
| development | local Postgres or SQLite | developer machines |
| test | fresh SQLite per test, or Postgres via `PDNA_TEST_DATABASE_URL` | CI and local tests |
| staging | managed Postgres (Supabase) | pre-release verification (not provisioned) |
| production | managed Postgres (Supabase) | not provisioned; needs owner authorization |
