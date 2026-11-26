# API specification

Machine-readable contract: `packages/api-client/openapi.json` (generated; served at `/openapi.json` and `/docs` outside production).

## Conventions

- Base path `/api/v1`. Breaking changes go to `/api/v2`.
- JSON only. Unknown request fields are rejected (422).
- Errors: `{"error": {"code": "snake_case", "message": "human text", "details": any}}`.
- Session-scoped endpoints require `X-Session-Token`. Missing, wrong and non-existent all return 404 `not_found`.
- `Cache-Control: no-store` on all API responses.

## Implemented endpoints

| Method | Path | Purpose | Notes |
| --- | --- | --- | --- |
| GET | `/health` | Liveness | |
| GET | `/api/v1/assessments` | List latest version of each instrument | Sorted by length |
| GET | `/api/v1/assessments/{id}` | Instrument detail with items and response options | Scoring keys are never exposed |
| POST | `/api/v1/assessment-sessions` | Start a session | Body: `instrument_id`, optional `version`, `locale`, `consent{accepted, age_confirmed_18_plus, policy_version}`. 201 with `resume_token` (shown once). Errors: 422 `consent_required`, `age_requirement`, `locale_unavailable`; 409 `consent_outdated`; 429 `rate_limited` |
| GET | `/api/v1/assessment-sessions/{id}` | Resume: status, answers, progress, result id | |
| PUT | `/api/v1/assessment-sessions/{id}/answers` | Upsert up to 500 answers; `value: null` clears | Idempotent. 409 `session_closed` after completion; 422 `unknown_item`, `invalid_answer` |
| POST | `/api/v1/assessment-sessions/{id}/complete` | Score and store result | Idempotent (returns the same result). 422 `incomplete` with `missing_items` and `insufficient_scales` |
| GET | `/api/v1/results/{id}` | Result with traits, archetypes, flags, methodology | |

## Accounts (implemented)

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/api/v1/auth/register` | 202 always (no account enumeration); emails a verification link |
| POST | `/api/v1/auth/verify-email` | `{token}` → user |
| POST | `/api/v1/auth/resend-verification` | 202 always |
| POST | `/api/v1/auth/login` | `{email, password, client}` → access token; web gets httpOnly refresh cookie, mobile gets `refresh_token` |
| POST | `/api/v1/auth/refresh` | Web: cookie + `X-PDNA-CSRF: 1`. Mobile: `{refresh_token}`. Rotates; reuse revokes the family |
| POST | `/api/v1/auth/logout` | Revokes the session family, clears cookie |
| POST | `/api/v1/auth/password-reset/request` | 202 always |
| POST | `/api/v1/auth/password-reset/confirm` | `{token, password}`; revokes all sessions and earlier access tokens |
| GET | `/api/v1/auth/me` | Current user |
| PATCH | `/api/v1/me` | Display name, locale |
| POST | `/api/v1/me/assessment-sessions/claim` | `{session_id, resume_token}` attaches a device session |
| GET | `/api/v1/personality/history` | All of the user's sessions and results |
| GET | `/api/v1/privacy/export` | Full JSON export |
| DELETE | `/api/v1/account` | `{password}`; deletes account and linked assessments |
| GET | `/api/v1/dev/outbox` | Development only, off unless `PDNA_DEV_OUTBOX_ENDPOINT=true`; refused in staging/production |

Session and result endpoints accept either the device `X-Session-Token` or the owner's bearer token.

## Planned (from MASTER_PROMPT.md §14)

Auth and profile, personality profile/history, coach conversations and messages (streaming via SSE), careers, growth plans and exercises, relationship invitations and shares, reports, subscriptions status, payment webhooks (signature-verified, idempotent), privacy export, account deletion, admin and enterprise APIs. Pagination will use opaque cursors (`?cursor=&limit=`). Idempotency keys (`Idempotency-Key` header) on payment and report-creation POSTs.
