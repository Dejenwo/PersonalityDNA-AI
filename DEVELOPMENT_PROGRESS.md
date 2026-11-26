# Development progress

The persistent tracker required by MASTER_PROMPT.md section 26. Statuses: Not Started, In Progress, Implemented, Tested, Verified, Blocked. "Tested" means automated tests ran and passed in this repository; "Verified" is reserved for independent human verification and is not used by agents.

Last updated: 2026-11-26.

## Phase overview

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| 1 | Product discovery | In Progress | PRD, MVP scope, research framework and licensing done. Competitor research is a framework only; customer interviews need the owner. |
| 2 | Architecture | Implemented | Architecture, database, API, AI, security docs and ADRs written. AI and payments are design only. |
| 3 | Repository foundation | Tested | Monorepo, tooling, CI, Docker files. Docker images not built in the dev sandbox (registry rate limit). CI not yet observed on GitHub. |
| 4 | Design system | In Progress | Tokens with contrast tests and web components. No icon, mobile components or `packages/ui` yet. |
| 5 | Authentication | Not Started | Next. Anonymous sessions with resume tokens exist and will link to accounts. |
| 6 | Assessment engine | Tested | Instruments, sessions, autosave, resume, deterministic scoring, versioning, audit. History is device-local until accounts exist. |
| 7 | Personality intelligence | In Progress | Big Five results, archetypes, trait explanations, strengths and growth. No shareable card or comparison yet. |
| 8–25 | Coaching onward | Not Started | See docs/PRODUCT_ROADMAP.md. |

## Task log

| ID | Module | Description | Priority | Status | Evidence |
| --- | --- | --- | --- | --- | --- |
| F-001 | Repo | Save master spec as MASTER_PROMPT.md | P0 | Implemented | Commit on main |
| F-002 | Repo | Monorepo (pnpm workspaces + Python service), .gitignore, .env.example | P0 | Implemented | `pnpm install` works from a clean checkout |
| F-003 | Science | Verify IPIP licence; record it | P0 | Implemented | assessment-content/licenses/IPIP.md (checked against ipip.ori.org on 2026-11-26) |
| F-004 | Assessment | Encode IPIP 50-item Big-Five markers, keyed as published | P0 | Tested | `test_bfm50_matches_published_keying` |
| F-005 | Assessment | Encode Mini-IPIP 20-item quick instrument | P0 | Tested | `test_mini_ipip_structure` |
| F-006 | Assessment | Content loader with schema validation and licence check | P0 | Tested | tests/test_content.py (6 tests) |
| F-007 | Scoring | Deterministic engine: reverse keying, prorated means, min-items rule, 0–100, bands, quality flags | P0 | Tested | tests/test_scoring.py (16 tests incl. hand-computed values) |
| F-008 | Personality | 16 original archetypes, deterministic mapping, weak-fit handling | P0 | Tested | tests/test_archetypes.py (4 tests, exhaustive 3^5 grid) |
| F-009 | Database | Models + Alembic migration 0001; schema matches models | P0 | Tested | tests/test_migrations.py on SQLite and PostgreSQL 16 |
| F-010 | Assessment | Version immutability: refuse edited released content | P0 | Tested | tests/test_versioning.py |
| F-011 | API | List/detail, create session (consent, 18+, policy version), save answers, resume, complete (idempotent), get result | P0 | Tested | tests/test_api.py (15 tests) |
| F-012 | Security | Resume tokens hashed (SHA-256), constant-time compare, 404 for unauthorized, rate limit, security headers, docs off in production | P0 | Tested | tests/test_api.py authorization, rate-limit, header tests |
| F-013 | Contract | OpenAPI export + generated TS types + typed client; CI drift check | P0 | Implemented | packages/api-client; `export_openapi.py --check` |
| F-014 | Design | Design tokens, light/dark, WCAG AA contrast tests, CSS/TS sync test | P0 | Tested | packages/design-tokens (4 tests) |
| F-015 | Web | Discover, intro + consent, questionnaire with autosave/retry/resume, review, results, history, privacy notice, error/empty/loading states | P0 | Tested | tests/e2e (5 scenarios × desktop + mobile = 10 passing) |
| F-016 | Web | Autosave queue (batching, ordering, retry, fatal errors) and device session store | P0 | Tested | apps/web vitest (7 tests) |
| F-017 | Accessibility | axe WCAG 2.2 AA scans on home, discover, intro, questionnaire, results | P0 | Tested | tests/e2e `expectAccessible`, zero violations |
| F-018 | DevOps | GitHub Actions: backend (SQLite + Postgres), web, e2e, secret scan; Dependabot; PR template | P0 | Implemented | .github/; not yet run on GitHub |
| F-019 | DevOps | Dockerfiles (non-root) and docker-compose with one-off migration job | P1 | Blocked | Written; build blocked in sandbox by Docker Hub 429. Needs a build in CI or locally. |
| F-020 | Docs | README, CLAUDE.md, AGENTS.md and docs/ set | P0 | Implemented | docs/ |
| A-001 | Auth | Accounts, email verification, password reset, sessions | P0 | Not Started | Phase 5 |
| A-002 | Auth | Link anonymous assessment sessions to an account | P0 | Not Started | Depends on A-001 |
| C-001 | Coaching | LLM provider interface + mock provider + safety layer | P0 | Not Started | Phase 8; real providers need API keys |
| M-001 | Monetization | Entitlements service with plan config; Stripe and RevenueCat webhooks | P0 | Not Started | Needs accounts; live keys needed for real payments |

## Test results (latest local run, 2026-11-26)

| Suite | Command | Result |
| --- | --- | --- |
| Backend, SQLite | `pytest` | 44 passed |
| Backend, PostgreSQL 16 | `PDNA_TEST_DATABASE_URL=... pytest` | 44 passed |
| Backend lint/types | `ruff check`, `ruff format --check`, `mypy app` (strict) | clean |
| Design tokens | `node --test` | 4 passed |
| Web unit | `vitest run` | 7 passed |
| Web types/lint/build | `tsc --noEmit`, `eslint .`, `next build` | clean, build succeeded |
| End-to-end + axe | `playwright test` (Chromium desktop + Pixel 7) | 10 passed |
