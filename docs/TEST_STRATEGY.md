# Test strategy

| Level | Tools | Where | Runs |
| --- | --- | --- | --- |
| Unit and integration (backend) | pytest, FastAPI test client against a real database | services/backend/tests | Every push, on SQLite and PostgreSQL 16; coverage gate 95% of lines |
| Unit (web and packages) | vitest, node:test | apps/web/src/**/*.test.ts, packages/design-tokens | Every push |
| Regression snapshots | Fixed answers for every instrument compared with stored results | tests/test_golden.py, tests/golden/*.json | Every push |
| Contract | OpenAPI export and generated-type drift checks | scripts/export_openapi.py --check | Every push |
| Migration | Alembic upgrade, compare with models, downgrade, data migrations | tests/test_migrations.py | Every push |
| Outbound integrations | SMTP and payment HTTP client with the network replaced | tests/test_integrations.py, tests/test_billing.py | Every push |
| End-to-end | Playwright (Chromium desktop and Pixel 7), production build | tests/e2e | Every push |
| Accessibility | axe-core (WCAG 2.0, 2.1 and 2.2 A/AA) in every flow, plus a sweep of every screen in light and dark mode | tests/e2e, specs/a11y-sweep.spec.ts | Every push |
| Security and privacy | Whole-API sweeps (sign-in, cross-account access, no 5xx), log privacy, complete deletion, headers, production guards; ruff `S`, gitleaks, pip-audit, pnpm audit | tests/test_security.py, CI | Every push |
| AI evaluation | Coach evaluation suite (safety, crisis, diagnosis, claims, bias, grounding, hallucination, injection, privacy) with the stand-in provider | scripts/run_coach_eval.py, docs/AI_EVALUATION.md | Every push; the live model run needs the owner's API key, spending cap and approval |
| Performance | Query budgets and foreign-key index check (pytest); page-weight budget (Playwright); load-test script | tests/test_performance.py, specs/perf-budget.spec.ts, scripts/load_test.py | Budgets every push; load test by hand against local or staging (docs/PERFORMANCE_TESTING.md) |

## Priorities

The most rigour goes to:

- **Scoring:** hand-computed expectations, determinism, version locks and regression snapshots.
- **Authorization:** whole-API sweeps plus per-domain ownership tests.
- **Privacy:** export completeness, deletion across every table, no private text in logs or notifications.
- **Payments:** webhook signatures and idempotency.
- **AI safety:** crisis routing, no diagnosis, grounding.

## Rules

- A failing test is fixed, never skipped or deleted to get green.
- A regression snapshot changes only with a deliberate change, and its diff is reviewed. When scoring arithmetic changes, `ENGINE_VERSION` is bumped first.
- A new public endpoint is added to the explicit public list in tests/test_security.py. Otherwise the sweep fails.
- Only failing tests are re-run while fixing; the full suite runs before a PR.
- Reports state the exact commands and results.

## Current counts

The latest run is in DEVELOPMENT_PROGRESS.md under "Test results". The QA report for Phase 22 is docs/QA_REPORT_2026-11-27.md.
