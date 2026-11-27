# PersonalityDNA AI

**Discover yourself. Understand others. Transform your life.**

An AI-assisted personality intelligence and personal development platform for iOS, Android and the web. The governing specification is [MASTER_PROMPT.md](MASTER_PROMPT.md); live status is in [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md).

> **Status: ready for a web beta, not yet launched.** The web app and API cover the features of the 25 phases in
> MASTER_PROMPT.md, apart from these open items: the Expo mobile app, shared UI and mobile design components, a live AI model run,
> real payment and email providers, deployment, external reviews (scientific, legal, clinical) and the beta itself.
> See [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md) and [docs/KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md).

## What works today

| Area | State |
| --- | --- |
| Assessments | Big Five (IPIP 50-item and Mini-IPIP 20-item), career interests (O*NET short form, draft), leadership preferences; autosave and resume |
| Results | Deterministic, versioned scoring; bands, archetypes, strengths and growth areas; no percentiles without norms |
| Personal growth | Growth programmes, emotional awareness and leadership modules, journal, goals and habits |
| Relationships and sharing | Two-person consented comparisons, reports with PDF download, revocable share cards |
| AI coach | Guarded coach with crisis routing and output checks; a labelled stand-in runs without any API key |
| Accounts and privacy | Sign-up with email confirmation, sessions, export, complete deletion, encrypted private text |
| Business | Plans and entitlements, Stripe and app-store billing (off until accounts exist), organisations, admin portal, feedback triage |
| Operations | Request ids and privacy-safe logs, readiness checks, smoke test, retention purge, reminders |
| Quality | 240+ backend tests on SQLite and PostgreSQL (97% coverage), web unit tests, Playwright end-to-end with axe on every screen, coach evaluation suite |

## Repository layout

```
apps/web                 Next.js web app, including the admin and organisation portals (mobile app: planned)
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
export PDNA_DEV_OUTBOX_ENDPOINT=true                 # emails appear at http://localhost:8000/api/v1/dev/outbox
alembic upgrade head
uvicorn app.main:app_factory --factory --reload      # http://localhost:8000/docs

# Web (new terminal, repo root)
pnpm install
NEXT_PUBLIC_API_URL=http://localhost:8000 pnpm dev:web   # http://localhost:3000
```

Locally no real email is sent: open the outbox link above to confirm an account. Payments are off, so every
feature is free, and the coach runs as a labelled stand-in. To open the admin portal, sign up, confirm the email,
then run `python scripts/grant_admin.py you@example.com superadmin` in `services/backend`.

Or with Docker (not yet tested end to end): `cp .env.example .env`, set `POSTGRES_PASSWORD`, then
`docker compose up --build`.

Deployment, operations and launch: [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md),
[docs/BETA_PROGRAM.md](docs/BETA_PROGRAM.md), [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

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
