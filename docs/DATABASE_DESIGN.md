# Database design

PostgreSQL 16 (Supabase in hosted environments). Schema is owned by Alembic migrations in `services/backend/alembic/versions`; `tests/test_migrations.py` proves the migrations produce exactly the ORM schema on SQLite and PostgreSQL.

Conventions: UUID primary keys (except content ids), `timestamptz` everywhere, foreign keys indexed, `ON DELETE` chosen per relation, check constraints for enums and ranges, no personal data in audit `details`.

## Implemented (migration 0001)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `assessment_instruments` | Instrument ids (e.g. `ipip-bfm-50`) | PK `id` | Permanent |
| `assessment_versions` | Registered content version: content JSON + SHA-256 | unique (instrument_id, version); FK RESTRICT | Permanent (needed to explain past results) |
| `consent_records` | Consent type, policy version, 18+ confirmation | `user_id` nullable until accounts | Life of related data + legal minimum |
| `assessment_sessions` | One attempt; hashed resume token; status; timestamps | status check; FKs to version and consent (RESTRICT) | Anonymous incomplete sessions: purge after 30 days (job pending) |
| `assessment_responses` | One row per answered item | unique (session_id, item_id); value 1–7 check; cascade on session delete | With session |
| `assessment_results` | Engine/instrument versions, hashes, archetype ranking (Big Five only, nullable since migration 0004), interest profile (interests only), quality flags | unique session_id; cascade | With session |
| `personality_trait_scores` | Per-trait status, raw mean, 0–100 score, band, answered/total | unique (result_id, trait); score 0–100 check | With result |
| `audit_events` | Security and lifecycle events (no answers, no PII) | indexed by type and time | 1 year (job pending) |

## Implemented (migration 0002, accounts)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `users` | Account: lower-cased unique email, Argon2id hash, verification time, profile | unique email; status check | Until deletion (hard delete) |
| `auth_tokens` | Single-use verification/reset tokens, SHA-256 only | unique hash; purpose check; cascade on user | Expire 24 h / 60 min; purge job pending |
| `refresh_tokens` | Rotating refresh tokens grouped by family | unique hash; cascade on user | 30 days; purge job pending |
| `assessment_sessions.user_id` | Owner after claim or signed-in start | FK CASCADE (deleting a user deletes their assessments) | |
| `consent_records.user_id` | Link to account | FK SET NULL (proof kept, unlinked) | |

## Implemented (migration 0003, AI coach)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `coach_conversations` | Owner, topic, consented result, consent record | FK user CASCADE; result SET NULL; consent RESTRICT | Until the user deletes it or the account |
| `coach_messages` | Encrypted message text (`content_encrypted`, AES-256-GCM bound to row id), role, kind, safety rule names, prompt version, provider, model | unique (conversation, sequence); role and kind checks; cascade on conversation | As conversation |
| `ai_usage_records` | Per-turn counts: provider, model, prompt version, outcome, tokens, latency, whether it counts toward the limit | FK user SET NULL (no content) | Kept for cost accounting |

Coaching consent is a `consent_records` row with type `ai_coaching`. `ai_context_grants` from the plan is not needed yet: each conversation records the single result the user chose.

## Implemented (migration 0004, career interests)

`assessment_results.interest_profile` (JSON: code, ranking, boundary ties, empty) for interest results; `archetype_version` and `archetypes` became nullable because interest results have no archetypes.

## Implemented (migration 0005, relationships)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `relationship_invitations` | Inviter, relation type, SHA-256 of the one-time token, inviter's consent, expiry | FK user CASCADE; consent SET NULL; unique token hash; type check | Deleted when accepted or cancelled; expired rows removed when the inviter next invites |
| `relationship_links` | Inviter, invitee, relation type, both consent records | FK users CASCADE; unique `pair_key` (sorted ids) so a pair has one link; type check | Deleted when either person ends it or deletes their account |

Comparisons are computed on request from each person's latest Big Five result and are never stored. Sharing consent is a `consent_records` row with type `relationship_sharing`.

## Implemented (migrations 0006 and 0007, learning tracks)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `learning_activity_progress` | Which learning activities a user marked done: track (`leadership`, `emotional-awareness`), module and activity ids and time, no free text | FK user CASCADE; unique (user, track, module, activity) | Until unmarked or account deletion |

## Implemented (migration 0012, share cards)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `share_cards` | Public cards the user chose to share: card content (profile name and description and/or bands, date) in the clear; link token hash for lookup and the token encrypted for the owner | FK user CASCADE; FK report CASCADE; unique token hash | Until the user stops sharing, deletes the report or deletes the account |

## Implemented (migration 0011, reports)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `reports` | Report snapshots: version, headline, result kinds used and creation time in the clear; the whole body encrypted (AES-256-GCM, row id as associated data) with its SHA-256 | FK user CASCADE; index (user, created) | Until the user deletes the report or the account |

## Implemented (migration 0010, goals and habits)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `goals` | Encrypted title and reason; target date, status, timestamps | FK user CASCADE; status check | Until deleted by the user or account deletion |
| `goal_milestones` | Encrypted title, due date, done time, position | FK goal CASCADE | As the goal |
| `habits` | Encrypted title, weekday mask (1–127), start date, pause time, optional goal | FK user CASCADE; FK goal SET NULL; days check | Until deleted |
| `habit_checks` | Local dates a habit was done | FK habit CASCADE; unique (habit, day) | As the habit |

## Implemented (migration 0009, journal)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `journal_entries` | Private entries: kind, entry date, optional mood (1–5) in the clear; title, text and tags encrypted (AES-256-GCM, row id and field as associated data) | FK user CASCADE; index (user, entry date); kind and mood checks | Until the user deletes the entry, the journal or the account |

## Implemented (migration 0008, growth programmes)

| Table | Purpose | Key constraints | Retention |
| --- | --- | --- | --- |
| `growth_enrollments` | A user following a programme (programme id, start and finish time) | FK user CASCADE; unique (user, programme) | Until the user leaves or restarts the programme, or deletes the account |
| `growth_day_progress` | Days marked done (day number and time, no free text) | FK enrolment CASCADE; unique (enrolment, day) | As the enrolment |
| `growth_check_ins` | Weekly self-checks (week number, rating 1 to 5) | FK enrolment CASCADE; unique (enrolment, week); rating between 1 and 5 | As the enrolment |

Migration 0006 created `leadership_activity_progress`; 0007 replaced it with `learning_activity_progress` and copied existing rows with track `leadership` (the downgrade copies leadership rows back and drops other tracks).

Leadership results reuse `assessment_results` and `personality_trait_scores`; they have neither archetypes nor an interest profile.

## Planned (by phase)

| Phase | Tables |
| --- | --- |
| 5 Auth | `users` (auth subject, status, created/deleted), `user_profiles`, `user_preferences`, `user_sessions` if not delegated; `assessment_sessions.user_id` FK |
| 7 | `share_cards` (opt-in, revocable public slug, minimal fields) |
| 9–11 | Additional instruments reuse assessment tables; `career_goals` |
| 10 | Implemented as `relationship_invitations` and `relationship_links` (above). Per-scope sharing beyond Big Five bands is not built |
| 13–14 | `development_programs`, `program_enrollments`, `exercises`, `exercise_completions`, `goals`, `habits`, `habit_records`, `journal_entries` (field-level encryption) |
| 15 | `reports` (generated artifact metadata; files in object storage) |
| 16 | `plans`, `prices` (remote config), `subscriptions`, `entitlements`, `payment_events` (idempotency key unique) |
| 17 | `admin_roles`, `feature_flags`, `content_reviews`, `feedback`, `support_requests` |
| 18 | `organizations`, `organization_members`, `programs`, `aggregate_reports` (k-anonymity threshold) |
| Privacy | `data_export_requests`, `account_deletion_requests` |

## Row-level security

When the database is Supabase, RLS policies in `database/policies/` will restrict every user-owned table to `auth.uid() = user_id`. The backend connects with a service role and enforces object-level authorization itself; RLS is defence in depth for any direct client access. Not yet written (Phase 5).

## Backups

Covered in DISASTER_RECOVERY.md.
