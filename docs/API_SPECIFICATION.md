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

## Journal (implemented)

Signed-in users only, except prompts. Entries belong to their author; other users get 404. Text is never logged.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/journal/prompts` | Kinds with prompts, mood scale, privacy and support notes (public) |
| GET | `/api/v1/journal/entries?cursor=&limit=` | Newest first (entry date, then creation time); opaque `next_cursor` |
| POST | `/api/v1/journal/entries` | Create (`kind`, `title`, `body`, `mood` 1–5, `tags`, `entry_date`) |
| GET / PATCH / DELETE | `/api/v1/journal/entries/{id}` | Read, change only the sent fields (null clears title or mood), delete |
| POST | `/api/v1/journal/search` | Words (all must match title, text or tags), tag, kind, date range, cursor, limit |
| GET | `/api/v1/journal/tags` | The user's tags with counts |
| GET | `/api/v1/journal/export?format=markdown\|json` | Download every entry (attachment, `no-store`) |
| POST | `/api/v1/journal/delete-all` | Delete every entry; body `{"confirm": true}` |

## Reports (implemented)

Signed-in users only; other users' reports return 404. A report is a snapshot and never changes after it is created.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/reports` | The user's reports, newest first (id, time, version, headline, result kinds used) |
| POST | `/api/v1/reports` | Create from the latest Big Five (required), interest and leadership results; 409 `no_results` without a Big Five result, 409 `too_many_reports` past 50 |
| GET / DELETE | `/api/v1/reports/{id}` | Read the full report body with its SHA-256, or delete it |
| GET | `/api/v1/reports/{id}/pdf` | The report as a PDF (attachment, `no-store`) |

## Administration (implemented)

Needs an admin role (`scripts/grant_admin.py` creates the first superadmin). A missing role or permission returns 404. Changes need a reason and are audited.

| Method | Path | Permission | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/admin/me` | any role | Roles and permissions |
| GET | `/api/v1/admin/users?q=` | users.read | Find accounts by email text or id (25 max) |
| GET | `/api/v1/admin/users/{id}` | users.read | Account metadata, counts, subscriptions, roles. Never private content |
| POST | `/api/v1/admin/users/{id}/status` | users.manage | Disable (signs out everywhere) or enable, with a reason |
| POST / DELETE | `/api/v1/admin/users/{id}/grants[/{sub}]` | subscriptions.manage | Complimentary Premium for 1–366 days, or remove it |
| POST / DELETE | `/api/v1/admin/users/{id}/roles[/{role}]` | roles.manage | Grant or remove admin roles |
| GET | `/api/v1/admin/metrics` | metrics.read | Accounts, assessments, subscriptions, estimated revenue, AI usage and cost, feature adoption (aggregates) |
| GET | `/api/v1/admin/content` | content.read | Engine, report, prompt and plan versions; instruments and content files with SHA-256 |
| GET | `/api/v1/admin/audit?before=&event_type=&limit=` | audit.read | Audit events, newest first |
| GET | `/api/v1/admin/health` | health.read | Database, environment and provider configuration |
| GET | `/api/v1/admin/organisations?q=` | orgs.read | Organisations by name or id: members, owners, seats, licence |
| PUT | `/api/v1/admin/organisations/{id}/licence` | orgs.manage (superadmin) | Record a pilot or a licence (seats, days, reason); audited |

## Languages (implemented)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/locales` | none | Supported languages with status (`planned`, `in_review`, `released`) and direction |
| PATCH | `/api/v1/me` `{locale}` | user | Save a released language to the profile; others return 422 `locale_unavailable` |

## Organisations (implemented)

Signed-in, verified accounts. Non-members get 404; members without the right role get 403. Join tokens travel in request bodies, never URLs.

| Method | Path | Who | Purpose |
| --- | --- | --- | --- |
| GET / POST | `/api/v1/orgs` | any | List mine; create (with `organisation_membership` consent) |
| GET | `/api/v1/orgs/catalog` | any | Growth programmes and learning modules programmes can use |
| POST | `/api/v1/orgs/invitations/preview` and `/accept` | any | See what a join link is for; join with consent (409 `seat_limit`, `already_member`) |
| GET / PATCH / DELETE | `/api/v1/orgs/{id}` | member / manager / owner | Detail with licence; rename; delete |
| DELETE | `/api/v1/orgs/{id}/membership` | member | Leave (409 `last_owner`) |
| PUT | `/api/v1/orgs/{id}/membership/sharing` | member | Opt in or out of group statistics |
| GET | `/api/v1/orgs/{id}/members` | manager | Names, emails, roles, join dates only |
| PUT / DELETE | `/api/v1/orgs/{id}/members/{member}[/role]` | owner / manager | Change role (owner); remove (admins remove members only) |
| GET / POST / DELETE | `/api/v1/orgs/{id}/invitations[/{inv}]` | manager | Open links; create (role, uses 1–500, days 1–30; token shown once); cancel |
| GET / POST / DELETE | `/api/v1/orgs/{id}/programs[/{program}]` | member / manager | List with own joined flag; create; delete |
| PUT / DELETE | `/api/v1/orgs/{id}/programs/{program}/participation` | member | Join or leave a programme |
| GET | `/api/v1/orgs/{id}/analytics` | manager | Members and seats; suppressed band distributions and programme counts |

## Growth and notifications (implemented)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/auth/register` `{attribution}` | none | Optional first-touch `referral`, `source`, `medium`, `campaign` (validated; unknown codes ignored) |
| GET | `/api/v1/referrals/me` | user | Stable code, link, count of verified accounts that joined with it, privacy note |
| POST | `/api/v1/analytics/events` `{name}` | none | Add one to today's count for a whitelisted event; always 204 |
| GET | `/api/v1/notifications[?before=]` | user | Newest 30 notifications, unread count, `next_before` cursor |
| POST | `/api/v1/notifications/{id}/read`, `/read-all` | user | Mark read (404 for someone else's) |
| GET / PUT | `/api/v1/notifications/preferences` | user | Per-kind `in_app` and `email`; 409 `required_notification` for security |

## Feedback (implemented)

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| POST | `/api/v1/feedback` `{kind, message, page?, app_version?, contact_ok}` | none or user | Send a problem, idea, wording, accessibility or other note (10 to 2,000 characters). The page is kept as a path only. 10 an hour per account or IP, then 429 |
| GET | `/api/v1/feedback` | user | Your own feedback (newest 50) with its status |
| GET | `/api/v1/admin/feedback[?status=&kind=&before=&limit=]` | `feedback.read` | Triage list with counts by status; the account id only when the sender agreed to be contacted |
| POST | `/api/v1/admin/feedback/{id}/status` `{status}` | `feedback.manage` | new, planned, fixed or closed; audited |

## Billing (implemented)

Gated features return 403 `premium_required` with `details.feature` once `PDNA_BILLING_ENFORCE=true`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/billing/plans` | Public plan list, prices, notes, whether checkout is available |
| GET | `/api/v1/billing/me` | The account's plan, features, coaching allowance, subscription and whether it can be managed here |
| POST | `/api/v1/billing/checkout` | `{plan_id}` → `{url}` of the payment page; 409 `already_subscribed`, 503 `billing_unavailable` |
| POST | `/api/v1/billing/manage` | `{url}` of the Stripe customer portal; 409 `manage_in_store` for app store subscriptions; 404 `no_subscription` |
| POST | `/api/v1/billing/restore` | Re-read app store purchases from RevenueCat |
| POST | `/api/v1/billing/webhooks/stripe` | Stripe events (signature required); not in the public schema |
| POST | `/api/v1/billing/webhooks/revenuecat` | RevenueCat events (shared secret); not in the public schema |

## Share cards (implemented)

Creating, listing and stopping a share needs an account; reading a card needs only its link token. Unknown, revoked and malformed tokens all return 404.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/share-cards` | The user's shared cards with their link tokens |
| POST | `/api/v1/share-cards` | Share a card from a report (`report_id`, `include_archetype`, `include_traits`); 422 `empty_card`, 409 `too_many_cards` past 10 |
| DELETE | `/api/v1/share-cards/{id}` | Stop sharing (the link stops working at once) |
| GET | `/api/v1/public/cards/{token}` | The card: profile name and description and/or trait bands, report date, note. `no-store`, `noindex` |
| GET | `/api/v1/public/cards/{token}/image.svg` | The card as a 1200 x 630 SVG with a text alternative |

## Goals and habits (implemented)

Signed-in users only; other users' goals and habits return 404. Habit endpoints take `?today=YYYY-MM-DD` (the person's local date, within a day of the server's).

| Method | Path | Purpose |
| --- | --- | --- |
| GET / POST | `/api/v1/goals` | List (active first) or create (title, why, target date, up to 20 milestones) |
| GET / PATCH / DELETE | `/api/v1/goals/{id}` | Read, adjust (only sent fields; status active, completed or archived), delete (linked habits are kept) |
| POST | `/api/v1/goals/{id}/milestones` | Add a milestone |
| PATCH / DELETE | `/api/v1/goals/{id}/milestones/{mid}` | Rename, set due date, mark done or not done; remove |
| GET / POST | `/api/v1/habits` | Habits with today's state, last 7 and 30 days (planned, done on planned, extra) and a four-week grid; create (title, weekdays 0–6, optional goal) |
| PATCH / DELETE | `/api/v1/habits/{id}` | Rename, change days or goal, pause or resume; delete |
| PUT / DELETE | `/api/v1/habits/{id}/checks/{day}` | Record or remove a done day (today or up to 30 days back) |

## Growth programmes (implemented)

Programmes are public to read; everything else needs an account. Progress calls on a programme the user has not started return 409 `not_enrolled`. Day and week numbers outside the programme return 404.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/growth/programs` | Programmes (kind `challenge` for 7 days, otherwise `program`), topics, objectives; with a signed-in user, enrolment summary (days done, next day, finished time) |
| GET | `/api/v1/growth/programs/{id}` | Weeks with objective, lesson, practice, self-check question, reflection, the user's rating and numbered days; review days |
| POST | `/api/v1/growth/programs/{id}/enrollment` | Start, or start again from day 1 (clears days and self-checks); returns the programme |
| DELETE | `/api/v1/growth/programs/{id}/enrollment` | Leave and delete progress |
| PUT / DELETE | `/api/v1/growth/programs/{id}/days/{day}/done` | Mark a day done (idempotent) or not done; finishing every day sets `completed_at` |
| PUT / DELETE | `/api/v1/growth/programs/{id}/weeks/{week}/check-in` | Save (`{"rating": 1..5}`) or clear a week's self-check |

## Planned (from MASTER_PROMPT.md §14)

Careers, growth plans and exercises, reports, subscriptions status, payment webhooks (signature-verified, idempotent), privacy export, account deletion, admin and enterprise APIs. Pagination will use opaque cursors (`?cursor=&limit=`). Idempotency keys (`Idempotency-Key` header) on payment and report-creation POSTs.
