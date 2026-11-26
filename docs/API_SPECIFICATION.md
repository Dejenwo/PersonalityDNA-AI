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

## Planned (from MASTER_PROMPT.md §14)

Auth and profile, personality profile/history, coach conversations and messages (streaming via SSE), careers, growth plans and exercises, relationship invitations and shares, reports, subscriptions status, payment webhooks (signature-verified, idempotent), privacy export, account deletion, admin and enterprise APIs. Pagination will use opaque cursors (`?cursor=&limit=`). Idempotency keys (`Idempotency-Key` header) on payment and report-creation POSTs.
