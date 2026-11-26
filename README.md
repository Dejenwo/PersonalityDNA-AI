# PersonalityDNA AI

**Discover yourself. Understand others. Transform your life.**

An AI-assisted personality intelligence and personal development platform for iOS, Android and the web. The governing specification is [MASTER_PROMPT.md](MASTER_PROMPT.md); live status is in [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).

> **Status: early development, not production ready.** The first vertical slice works end to end: pick an assessment, give consent, answer with autosave and resume, get deterministic Big Five scores, archetypes and a results report. Accounts, AI coaching, payments, mobile and the admin and enterprise portals are not built yet. See [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## What works today

| Area | State |
| --- | --- |
| Big Five instruments | IPIP 50-item (comprehensive) and Mini-IPIP 20-item (quick), public domain, licence verified |
| Scoring | Deterministic, versioned, audited (content hash + answers hash stored with every result) |
| Archetypes | 16 original descriptive archetypes, deterministic primary/secondary mapping |
| Backend API | FastAPI, versioned REST, consent + 18+ gate, per-session resume tokens, rate limiting |
| Database | SQLAlchemy models + Alembic migration, tested on SQLite and PostgreSQL 16 |
| Web app | Next.js 16: marketplace, consent, one-statement-at-a-time questionnaire with autosave/offline retry/resume, results report, history |
| Quality | 44 backend tests, 11 web/package unit tests, 10 Playwright end-to-end runs (desktop + mobile) including axe WCAG 2.2 AA scans |

## Repository layout

```
apps/web                 Next.js web app (mobile, admin, enterprise apps: planned)
services/backend         FastAPI modular monolith (app/, tests/, alembic/)
packages/api-client      Typed API client generated from the backend OpenAPI document
packages/design-tokens   Colour, type and spacing tokens with WCAG contrast tests
packages/configuration   Shared TypeScript config
assessment-content       Versioned instruments, scoring rules, archetypes, licence records
tests/e2e                Playwright end-to-end and accessibility tests
docs/                    Product, architecture, science, security and operations docs
```

## Run it locally

Prerequisites: Python 3.12+, Node 22, pnpm 10, and PostgreSQL 16 (or use SQLite for a quick start).

```bash
# Backend
cd services/backend
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
export PDNA_DATABASE_URL=sqlite:///./pdna-local.db   # or a postgresql+psycopg:// URL
alembic upgrade head
uvicorn app.main:app_factory --factory --reload      # http://localhost:8000/docs

# Web (new terminal, repo root)
pnpm install
NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm dev:web   # http://localhost:3000
```

Or with Docker: `cp .env.example .env`, set `POSTGRES_PASSWORD`, then `docker compose up --build`.

## Tests

```bash
cd services/backend && pytest                       # SQLite
PDNA_TEST_DATABASE_URL=postgresql+psycopg://... pytest   # PostgreSQL
ruff check . && ruff format --check . && mypy app

pnpm -r typecheck && pnpm --filter @pdna/web lint
pnpm --filter @pdna/design-tokens test && pnpm --filter @pdna/web test
pnpm --filter @pdna/web build && pnpm e2e           # starts backend + web itself
```

After changing the API, run `pnpm api:generate` to refresh `packages/api-client`.

## Principles

- Scores come from a documented, deterministic formula. AI never scores assessments.
- No scientific validation, population percentile or accuracy claim is made without evidence.
- Not a clinical tool, and never for hiring or employment decisions.
- Private by default: no assessment data is sold or used for model training.

## Licence

Proprietary. All rights reserved by the project owner. Third-party content licences are recorded in [assessment-content/licenses](assessment-content/licenses) and [docs/ASSESSMENT_LICENSES.md](docs/ASSESSMENT_LICENSES.md).
