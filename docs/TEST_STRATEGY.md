# Test strategy

| Level | Tools | Where | Runs |
| --- | --- | --- | --- |
| Unit (backend) | pytest | services/backend/tests | Every push (CI), SQLite and PostgreSQL |
| Unit (web/packages) | vitest, node:test | apps/web/src/**/*.test.ts, packages/design-tokens | Every push |
| Contract | OpenAPI export + generated types drift check | scripts/export_openapi.py --check | Every push |
| Migration | Alembic upgrade + compare to models + downgrade | tests/test_migrations.py | Every push |
| End-to-end | Playwright (Chromium desktop + Pixel 7 emulation) | tests/e2e | Every push |
| Accessibility | axe-core in e2e (WCAG 2.0/2.1/2.2 A/AA tags) | tests/e2e | Every push |
| Security | ruff `S` rules, gitleaks, pip-audit, pnpm audit | CI | Every push |
| AI evaluation | See AI_EVALUATION.md | ai/evaluations | Planned |
| Performance | k6 or Locust | tests/performance | Planned (PERFORMANCE_TESTING.md) |

## Priorities

Most rigour on scoring (hand-computed expectations, determinism, version locks), authorization (cross-session access attempts), and later payments (webhook signatures, idempotency) and privacy (export completeness, deletion).

## Rules

- A failing test is fixed, never skipped or deleted to get green.
- Only failing tests are re-run while fixing; the full suite runs before a PR.
- Reports state the exact commands and results.

## Current counts (2026-11-26)

Backend 44 · design tokens 4 · web unit 7 · e2e 10 (5 scenarios × 2 devices).
