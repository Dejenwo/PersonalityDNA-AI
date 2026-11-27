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
| GET | `/api/v1/assessments` | List latest version of each instrument | Big Five first, then by length; each has `family` and `status` (drafts only outside production) |
| GET | `/api/v1/assessments/{id}` | Instrument detail with items and response options | Scoring keys are never exposed |
| POST | `/api/v1/assessment-sessions` | Start a session | Body: `instrument_id`, optional `version`, `locale`, `consent{accepted, age_confirmed_18_plus, policy_version}`. 201 with `resume_token` (shown once). Errors: 422 `consent_required`, `age_requirement`, `locale_unavailable`; 409 `consent_outdated`; 429 `rate_limited` |
| GET | `/api/v1/assessment-sessions/{id}` | Resume: status, answers, progress, result id | |
| PUT | `/api/v1/assessment-sessions/{id}/answers` | Upsert up to 500 answers; `value: null` clears | Idempotent. 409 `session_closed` after completion; 422 `unknown_item`, `invalid_answer` |
| POST | `/api/v1/assessment-sessions/{id}/complete` | Score and store result | Idempotent (returns the same result). 422 `incomplete` with `missing_items` and `insufficient_scales` |
| GET | `/api/v1/results/{id}` | Result with traits, archetypes, flags, methodology | `kind` is `big_five` (with `archetypes`) or `interests` (with `interests`: code, areas, ties, explore links, `draft`) |

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

## AI coach (implemented)

Signed-in, verified users only. Conversations belong to one user; others get 404.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/coach/status` | Enabled, demo mode, consent policy version, daily limit, used, remaining, reset time, whether results exist |
| GET | `/api/v1/coach/conversations` | The user's conversations, newest first |
| POST | `/api/v1/coach/conversations` | `{consent: {accepted, policy_version}, topic, use_results, result_id?}`; 409 `consent_outdated` |
| GET | `/api/v1/coach/conversations/{id}` | Conversation with decrypted messages |
| DELETE | `/api/v1/coach/conversations/{id}` | Permanent delete (usage counts are kept) |
| POST | `/api/v1/coach/conversations/{id}/messages` | `{content}` (1–4000 chars). 429 `coach_limit_reached` (details.resets_at), 409 `coach_busy`. Otherwise `text/event-stream` with events `start`, `delta {text}`, `retract` (discard text so far), `done {user_message, assistant_message, remaining}` or `error {code, message, retryable}`. On `error` nothing is saved |

## Relationships (implemented)

Signed-in, verified users only. A link is visible only to its two people; others get 404. Tokens travel in request bodies, never URLs.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/relationships` | Policy version, the user's open invitations and links |
| POST | `/api/v1/relationships/invitations` | `{relation_type, consent: {accepted, policy_version}}` → 201 with the one-time `token`. 409 `consent_outdated`; 429 `too_many_invitations` (10 open) |
| DELETE | `/api/v1/relationships/invitations/{id}` | Cancel (inviter only) |
| POST | `/api/v1/relationships/invitations/preview` | `{token}` → inviter display name, relation type, expiry, policy version. 404 `invitation_not_found` |
| POST | `/api/v1/relationships/invitations/accept` | `{token, consent}` → 201 link. 409 `own_invitation`, `already_linked`, `consent_outdated`; 404 if used, cancelled or expired |
| GET | `/api/v1/relationships/{id}` | Comparison: per trait `you`/`them` band, pattern (`similar`, `some_difference`, `different`), summary, note, possible misunderstanding, prompt; plus exercises and shared goals. `missing_results` lists who has no Big Five result. No scores |
| DELETE | `/api/v1/relationships/{id}` | Either person ends the link for both |

## Leadership (implemented)

Results of the `leadership-preferences-27` instrument come back from the normal result endpoints with `kind: "leadership"` and a `leadership` block (areas ranked with scores and text, top, stretch, even, recommended modules, note).

Development modules are served by the learning endpoints below with `{track}` = `leadership`.

## Learning tracks (implemented)

Tracks: `leadership` and `emotional-awareness` (no score, ADR-015). Unknown tracks, modules and activities return 404.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/learning/{track}/modules` | Track title, note, optional support note and module catalogue; with a signed-in user, activities done per module |
| GET | `/api/v1/learning/{track}/modules/{id}` | Lessons, activities (with `completed_at` for the signed-in user), reflection and support note |
| PUT | `/api/v1/learning/{track}/modules/{id}/activities/{activity}/done` | Mark done (account required, idempotent) |
| DELETE | `/api/v1/learning/{track}/modules/{id}/activities/{activity}/done` | Mark not done |

The coach accepts the topic `emotions` ("Emotions and communication").

## Planned (from MASTER_PROMPT.md §14)

Careers, growth plans and exercises, reports, subscriptions status, payment webhooks (signature-verified, idempotent), privacy export, account deletion, admin and enterprise APIs. Pagination will use opaque cursors (`?cursor=&limit=`). Idempotency keys (`Idempotency-Key` header) on payment and report-creation POSTs.
