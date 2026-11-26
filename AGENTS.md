# AGENTS.md

Instructions for AI coding agents (Cursor, Codex, Claude Code and others). CLAUDE.md holds the same rules.

## Start of every session

1. Read `MASTER_PROMPT.md` (governing spec), `DEVELOPMENT_PROGRESS.md` (tracker) and `docs/ARCHITECTURE_DECISIONS.md`.
2. `git status` and `git log --oneline -10`. Never restart work that is already done.
3. Run the existing tests before changing anything, so you know the baseline.

## Non-negotiables

- **Scoring is deterministic and AI-free.** `services/backend/app/scoring/engine.py` is pure. Any change to scoring arithmetic bumps `ENGINE_VERSION` and adds tests with hand-computed expectations.
- **Released assessment content is immutable.** Never edit `assessment-content/instruments/*.json` once released; add a new version file. The backend refuses to start if a released file changes.
- **Every instrument needs a licence record** in `assessment-content/licenses/`. Do not add MBTI, DISC, Enneagram, StrengthsFinder or other proprietary items.
- **No invented science or business facts.** No percentiles without norm data, no validation claims, no fabricated market statistics.
- **Not clinical, not for hiring.** Never add diagnostic language or employment screening.
- **Privacy:** never log answers, journal text or coaching content. Never send personal data to AI providers without the user's authorization. Admin users must not read private journals or coaching conversations.
- **Secrets:** never commit `.env` or keys. Configuration comes from `PDNA_*` environment variables.
- **Report honestly:** do not claim tests passed unless you ran them and saw them pass.

## Commands

```bash
# backend (services/backend)
pytest                                  # SQLite
PDNA_TEST_DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/db pytest
ruff check . && ruff format --check . && mypy app
alembic revision --autogenerate -m "..."   # then review the file by hand
python scripts/export_openapi.py        # after API changes; then pnpm api:generate

# web and packages (repo root)
pnpm -r typecheck && pnpm --filter @pdna/web lint
pnpm --filter @pdna/web test && pnpm --filter @pdna/design-tokens test
pnpm --filter @pdna/web build && pnpm e2e
```

## Conventions

- Backend: modular monolith. Each domain is a package under `app/` (assessments, scoring, personality, ...). Routes stay thin; logic lives in `service.py` modules; responses are built in presenters.
- Errors use the envelope `{"error": {"code", "message", "details"}}` via `ApiError`.
- Object-level authorization on every read and write. Unknown and unauthorized resources both return 404.
- Web: client components call the typed client in `packages/api-client`. Every screen has loading, empty, error and success states. Accessibility is tested with axe in `tests/e2e`.
- Design tokens live in `packages/design-tokens`; do not hard-code colours.
- Update `DEVELOPMENT_PROGRESS.md` and relevant docs in the same change as the code.
