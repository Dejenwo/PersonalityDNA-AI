# Development progress

The persistent tracker required by MASTER_PROMPT.md section 26. Statuses: Not Started, In Progress, Implemented, Tested, Verified, Blocked. "Tested" means automated tests ran and passed in this repository; "Verified" is reserved for independent human verification and is not used by agents.

Last updated: 2026-11-27.

## Phase overview

| Phase | Name | Status | Notes |
| --- | --- | --- | --- |
| 1 | Product discovery | In Progress | PRD, MVP scope, research framework and licensing done. Competitor research is a framework only; customer interviews need the owner. |
| 2 | Architecture | Implemented | Architecture, database, API, AI, security docs and ADRs written. AI and payments are design only. |
| 3 | Repository foundation | Tested | Monorepo, tooling, CI, Docker files. Docker images not built in the dev sandbox (registry rate limit). CI not yet observed on GitHub. |
| 4 | Design system | In Progress | Tokens with contrast tests and web components. No icon, mobile components or `packages/ui` yet. |
| 5 | Authentication | Tested | Email/password accounts, verification, reset, rotating sessions, claim, history, export, deletion (ADR-010). No social login or MFA yet. |
| 6 | Assessment engine | Tested | Instruments, sessions, autosave, resume, deterministic scoring, versioning, audit. History is device-local until accounts exist. |
| 7 | Personality intelligence | In Progress | Big Five results, archetypes, trait explanations, strengths and growth. Shareable cards in Phase 15; comparison in Phase 10. |
| 8 | AI coaching | Tested | Provider interface (stand-in + Anthropic), consented context from scores only, versioned prompt, crisis routing, input flags, streaming output guard, grounding check, encrypted messages, daily limits, usage records, evaluation suite, web chat (ADR-011). Live model not yet run: needs the owner's API key and spending cap. |
| 9 | Career intelligence | Tested | O*NET Interest Profiler Short Form (60 activities) as a **draft** instrument, count-based RIASEC scoring (engine 1.1.0), interest code with tie reporting, interest results page, career exploration page joining interests and Big Five working style, interests in coach context (ADR-012). Draft is hidden in production until the wording is checked against the official PDF and a lawyer confirms the CC BY-ND reading. |
| 10 | Relationship intelligence | Tested | One-time invitation links, consent from both people, one link per pair, comparison of Big Five bands with original similarity, difference, misunderstanding and prompt text, exercises and shared goals, revoke by either person, export and deletion (ADR-013). No compatibility score or prediction. |
| 11 | Leadership intelligence | Tested | Original 27-statement leadership preferences questionnaire (9 areas from the spec, labelled unvalidated), ranked results with build and stretch suggestions, 9 development modules with lessons, activities and reflection, activity progress for accounts, leadership preferences in coach context (ADR-014). Never presented as ability or used for employment decisions. |
| 12 | Emotional awareness | Tested | Original learning track: 7 modules (self-awareness, reflective communication, active listening, empathy, stress reflection, interpersonal understanding, constructive expression) with lessons, activities, reflection and a support note; no score or test; shared learning-track API and progress (migration 0007); "Emotions and communication" coach topic; Learn page (ADR-015). Needs a clinical safety review of wording before launch. |
| 13 | Personal growth academy | Tested | Original content: 12 weekly units across the 10 topics in the spec, composed into three 7-day challenges and 30, 60 and 90-day programmes with objectives, lessons, practice, daily exercises, weekly milestones, review days and weekly 1 to 5 self-checks; enrolment, day progress and self-checks for accounts (migration 0008); Learn page entry (ADR-016). Annual goals move to Phase 14 goals. |
| 14 | Journaling, goals and habits | Tested | Journal: encrypted entries (title, text, tags), six kinds with original prompts, optional mood, tags, search after decryption (POST, not logged), Markdown and JSON export, delete one or all (ADR-017). Goals with milestones and adjustment, habits on chosen weekdays with history, neutral 7 and 30-day summaries and a four-week grid, no streaks (ADR-018). Reminders wait for the notification service. |
| 15 | Reports | Tested | Personality reports: a snapshot of the latest Big Five, interest and leadership results with profile, trait scores as text and bars, strengths, development, communication and relationship guidance, career interests, leadership preferences, values note, a development plan of growth programmes and leadership modules, methodology, references and limitations; stored encrypted with a body fingerprint (migration 0011); report library, report page and server-rendered PDF download (ADR-019). Shareable personality cards: opt-in, revocable public links with profile name and Big Five bands only, an SVG image, no name, email or scores (migration 0012, ADR-020). |
| 16 | Monetization | Tested | Plans and prices as validated data; entitlement service (report PDFs, programmes over 7 days, relationship invitations, coaching allowance); Stripe checkout, customer portal and signed, idempotent webhooks; RevenueCat webhooks and restore for Apple and Google; local checkout for development; pricing page and plan card on the account page (migration 0013, ADR-021). Off until the owner sets up providers (`PDNA_BILLING_ENFORCE`). |
| 17 | Administration | Tested | Five least-privilege roles (first superadmin from the command line), account search and detail without private content, disable or enable with sign-out, complimentary Premium, role management, metrics (accounts, assessments, subscriptions, estimated revenue, AI tokens and cost, feature adoption), content and version overview, audit log, health; every change audited with a reason (migration 0014, ADR-022). |
| 18 | Enterprise portal | Tested | Organisations with owner, admin and member roles; join links with seat limits; voluntary membership with its own consent; programmes built from growth programmes and learning modules that members choose to join; group statistics only from members who opt in, shown for 10 or more with every band at least 3; programme counts under 3 hidden; organisations never see individual results or who opted in; seat licences recorded by a superadmin give members Premium features; ownership handed over on account deletion; export (migration 0015, ADR-023). |
| 19–25 | Internationalisation onward | Not Started | See docs/PRODUCT_ROADMAP.md. |

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
| A-001 | Auth | Accounts: register (consent, 18+, policy version), email verification, login, rotating refresh with reuse detection, logout, password reset | P0 | Tested | tests/test_auth.py; e2e account.spec.ts |
| A-002 | Auth | Claim anonymous sessions into an account; owner access without device token | P0 | Tested | `test_claim_history_and_owner_access`; e2e claim journey |
| A-003 | Privacy | Data export (JSON) and account deletion with cascade; consent proof retained unlinked | P0 | Tested | `test_export_and_delete_account`; e2e |
| A-004 | Security | Production settings guards; auth rate limiting; generic errors; no account enumeration on register/reset | P0 | Tested | `test_production_settings_guards`, `test_login_rate_limited`, `test_registration_does_not_reveal_existing_accounts` |
| A-005 | Web | Register, login, verify, forgot/reset password, account page (profile, export, sign out, delete), account history | P0 | Tested | e2e (8 account runs) + axe |
| A-006 | Auth | Social login (Apple/Google), MFA, purge job for unverified accounts | P1 | Not Started | Apple/Google need developer accounts |
| C-001 | Coaching | LLM provider interface; deterministic stand-in; Anthropic provider (streaming, prompt caching of shared instructions only, effort setting, refusal and error mapping) | P0 | Tested | tests/test_coach.py provider tests (fake SDK client); no live call made |
| C-002 | Coaching | Conversations: consent record, result authorization, history window, encryption at rest (AES-256-GCM bound to row id), export and deletion | P0 | Tested | tests/test_coach.py (conversation, privacy, cipher tests) |
| C-003 | Safety | Crisis routing before the model (also at the limit), input flags, streaming output guard with retraction, refusal handling, grounding check, audit events without content | P0 | Tested | tests/test_coach.py safety tests; docs/AI_SAFETY.md |
| C-004 | Coaching | Rolling 24-hour message limit, one reply at a time per conversation, usage records (tokens, latency, outcome) | P0 | Tested | `test_daily_limit`, `test_one_reply_at_a_time_per_conversation` |
| C-005 | Evaluation | Case suite (crisis, diagnosis, grounding, hallucination, claims, injection, privacy, bias) and runner; stand-in passes all thresholds in CI | P0 | Tested | ai/evaluations/coach/cases.json; scripts/run_coach_eval.py; `test_evaluation_*` |
| C-006 | Web | Coach home (status, demo notice, topics, consent), streaming chat, crisis support card, delete, sign-in redirect back, results-page entry | P0 | Tested | e2e coach.spec.ts (desktop + mobile) + axe; vitest SSE parser and safe text renderer |
| C-007 | Coaching | Live evaluation against Claude; OpenAI provider; plan-based limits; goals and progress in context; human review sampling | P1 | Not Started | Needs API key and spending cap (live eval ≈ 32 calls); OpenAI only if the owner wants a second provider |
| R-001 | Science | O*NET Interest Profiler Short Form licence record (CC BY-ND 4.0, attribution, trademark rules) and draft instrument | P0 | Implemented | assessment-content/licenses/ONET.md; wording not yet verified (onetcenter.org blocked from the sandbox) |
| R-002 | Assessment | Draft status: drafts load only outside production, may change until released, then become immutable | P0 | Tested | `test_drafts_*`, `test_draft_may_change_but_released_may_not` |
| R-003 | Scoring | `count_endorsed` scoring (engine 1.1.0; Likert arithmetic unchanged) and interest profile (code, Holland-order tie break, reported ties) | P0 | Tested | tests/test_careers.py hand-computed tests |
| R-004 | API | Interest results (`kind`, `interests`), family and status in listings, history label, migration 0004 | P0 | Tested | `test_interest_assessment_end_to_end`; migration test on SQLite and PostgreSQL |
| R-005 | Coaching | Coach context includes the latest interest result alongside the Big Five result, only when results are shared | P0 | Tested | `test_interest_results_in_history_and_coach_context`, `test_coach_context_with_only_interests` |
| R-006 | Web | Interest results page, career exploration page (interests, working-style questions, explore links, coach entry), preview badges, O*NET attribution, wrapping nav | P0 | Tested | e2e careers.spec.ts (desktop + mobile) + axe; vitest careers helpers |
| R-007 | Careers | Occupation search (O*NET Web Services), saved careers, skills gaps, learning paths | P1 | Not Started | Needs O*NET Web Services registration and terms review |
| L-001 | Relationships | Invitations (hashed one-time token, 7-day expiry, 10 open max), preview, accept with consent, cancel; one link per pair | P0 | Tested | tests/test_relationships.py |
| L-002 | Relationships | Band comparison (similar, some difference, different) and original insight content; no scores shared | P0 | Tested | `test_patterns`, `test_compare_texts`, `test_content_has_no_scores_or_predictions` |
| L-003 | Privacy | Either person revokes; strangers get 404; export includes own links; account deletion removes links | P0 | Tested | `test_invite_accept_compare_and_revoke`, `test_export_and_account_deletion` |
| L-004 | Web | Relationships page (invite, copy link, open invitations, links), join page (token kept through sign-in, removed from address bar), comparison page with end confirmation | P0 | Tested | e2e relationships.spec.ts (two users, desktop + mobile) + axe; vitest invite helpers |
| L-005 | Relationships | Email invitations, per-scope sharing (interests, goals), coach use of shared comparison | P2 | Not Started | Only with explicit consent design; coach must never see the other person's data without it |
| D-001 | Assessment | Leadership preferences questionnaire (original, 27 items, interleaved, likert_mean, no bands) | P0 | Tested | `test_instrument_and_program` |
| D-002 | Leadership | Deterministic profile: ranking with content-order ties, top three, two stretch areas, even-profile rule, module recommendations | P0 | Tested | `test_profile_*`, `test_leadership_result` |
| D-003 | Leadership | Module catalogue and detail (public), activity progress (accounts, idempotent), export, migration 0006 (now learning tracks, E-002) | P0 | Tested | `test_modules_and_progress` |
| D-004 | Coaching | Leadership preferences in coach context when results are shared | P0 | Tested | `test_history_and_coach_context` |
| D-005 | Web | Leadership results, leadership hub (suggested modules, all modules with progress), module pages with done toggles; shared latest-results hook | P0 | Tested | e2e leadership.spec.ts (desktop + mobile) + axe |
| D-006 | Leadership | Validation study, team or 360 views, manager programmes | P2 | Not Started | Needs a psychometrics reviewer; 360 views need a separate consent design and must never feed employment decisions |
| E-001 | Content | Emotional awareness track: 7 original modules, note (not therapy, no score) and support note | P0 | Tested | `test_emotional_awareness_content` |
| E-002 | Learning | Leadership and emotional awareness served as learning tracks; progress per track and user; export `learning_activities`; migration 0007 copies leadership progress | P0 | Tested | tests/test_learning.py, `test_0007_moves_leadership_progress_into_learning_tracks` (SQLite and PostgreSQL) |
| E-003 | Coaching | "Emotions and communication" topic with not-therapy, no-diagnosis, no-rating instructions | P0 | Tested | `test_emotions_coach_topic`; coach evaluation at threshold |
| E-004 | Web | Learn page, emotional awareness hub and module pages with support note, shared module components, coach topic | P0 | Tested | e2e emotional-awareness.spec.ts and leadership.spec.ts (desktop + mobile) + axe |
| E-005 | Emotional awareness | Clinical safety review of wording; crisis resources per country; optional private reflection notes (with Phase 14 journal encryption) | P1 | Not Started | Needs a qualified reviewer; reflection notes wait for field-level encryption |
| G-001 | Content | Growth academy: 12 original weekly units, 7 programmes (7, 30, 60, 90 days), review days, self-check scale | P0 | Tested | `test_programme_lengths_and_content`, `test_plan_week_structure` |
| G-002 | Growth | Deterministic day plan (lesson, five exercises, milestone per week; review days) and next-day rule | P0 | Tested | `test_plan_week_structure`, `test_next_day` |
| G-003 | Growth | Enrol, restart, leave; day progress (idempotent, finish time kept in sync); weekly self-checks; export; deletion; migration 0008 | P0 | Tested | `test_enrol_progress_check_in_and_restart`, `test_account_deletion_removes_growth_progress`; migration test on SQLite and PostgreSQL |
| G-004 | Web | Growth hub (your programmes, challenges, programmes) and programme page (status, next up, weekly plan with day toggles, self-check radios, confirm before restart or leave) | P0 | Tested | e2e growth.spec.ts (desktop + mobile) + axe; vitest growth helpers |
| G-005 | Growth | Reminders and notifications, coach awareness of the current programme (with sharing consent), learning-platform export (LTI/xAPI), learning-designer review | P2 | Not Started | Reminders need the notification service (later phase); coach use needs a sharing choice |
| J-001 | Journal | Entries encrypted at rest (AES-256-GCM, row id and field bound); kind, date and mood in the clear; limits; owner-only access | P0 | Tested | `test_entries_are_encrypted_and_private`, `test_create_validation` |
| J-002 | Journal | Update only sent fields, pagination with opaque cursors, search by words, tag, kind and dates, tag counts | P0 | Tested | `test_update_list_and_pagination`, `test_search_and_tags`, `test_tag_normalisation_and_cursor` |
| J-003 | Privacy | Markdown and JSON export, privacy export, delete one, delete all, account deletion; text never logged | P0 | Tested | `test_export_and_deletion`, `test_journal_text_is_never_logged` |
| J-004 | Web | Journal list with search and filters, new entry with prompts, entry view, edit and delete, downloads, delete all with confirmation; nav link | P0 | Tested | e2e journal.spec.ts (desktop + mobile) + axe; vitest journal helpers |
| J-005 | Journal | Optional AI reflection on entries (separate consent), mood charts, attachments, KMS-held keys and rotation | P2 | Not Started | AI use needs its own consent design; keys are a deployment task |
| H-001 | Goals | Goals with encrypted title and reason, target date, status changes, milestones (add, rename, done, remove), deletion keeps habits | P0 | Tested | `test_goal_lifecycle_and_privacy`, `test_goal_validation` |
| H-002 | Habits | Weekday schedules, local-date checks (30-day back-fill), pause, goal link, deletion, export | P0 | Tested | `test_habit_checks_history_and_stats`, `test_habits_link_to_goals_archive_and_delete` |
| H-003 | Habits | Pure analytics: masks, 7 and 30-day windows from the start date, extra days, four-week grid; no streaks | P0 | Tested | `test_masks`, `test_window_counts_planned_and_extra_days`, `test_grid_is_whole_weeks_ending_this_week` |
| H-004 | Web | Goals and habits page (today's habits, history grid, pause, new habit and goal forms) and goal page (adjust, milestones, complete, archive, delete, reflection links); nav link | P0 | Tested | e2e goals.spec.ts (desktop + mobile) + axe; vitest habit helpers |
| H-005 | Habits | Opt-in reminders with quiet hours; annual goals view; coach awareness with a sharing choice | P1 | Not Started | Reminders need the notification service |
| R-001 | Reports | Deterministic report builder from the latest result of each kind and versioned original content; plan grounded in existing programmes and modules; content fingerprint | P0 | Tested | `test_build_is_deterministic_and_plan_is_grounded` |
| R-002 | Reports | Encrypted storage, library, read, PDF (attachment, `no-store`), delete, 50-report limit, owner-only access, privacy export, account deletion | P0 | Tested | `test_create_read_pdf_and_delete`, `test_reports_belong_to_their_owner`, `test_report_limit`, `test_export_and_account_deletion` |
| R-003 | Web | Report library with create, report page with every section as text, PDF download, delete with confirmation; link from My results | P0 | Tested | e2e reports.spec.ts (desktop + mobile) + axe; vitest report helpers |
| R-004 | Sharing | Share cards from a report: choose profile and/or bands, public read and SVG image without sign-in (`no-store`, `noindex`, strict CSP on the SVG), token hashed for lookup and encrypted for the owner, stop sharing, 10-card limit, removed with the report or account, in the privacy export | P1 | Tested | tests/test_sharing.py (4 tests); e2e reports.spec.ts share steps + axe; vitest share helpers |
| R-006 | Sharing | PNG image for social previews (needs server-side rendering of the page with Open Graph tags) | P2 | Not Started | Links carry the token in the fragment, so previews would need a different link design |
| R-005 | Reports | Values assessment section (needs a licensed values instrument); PDF accessibility tagging (PDF/UA) | P2 | Not Started | reportlab does not produce tagged PDFs; the web report is the accessible version |
| M-001 | Monetization | Plan config validation; entitlement service and enforcement points; coaching allowance by plan | P0 | Tested | `test_plan_config_and_helpers`, `test_everything_available_until_enforced`, `test_free_plan_limits_and_upgrade` |
| M-002 | Monetization | Stripe checkout and portal (fake HTTP), webhook signatures, idempotency, status mapping, customer reuse | P0 | Tested | `test_stripe_signature_verification`, `test_stripe_checkout_webhooks_and_portal` |
| M-003 | Monetization | RevenueCat webhooks (auth, purchase, cancellation, expiry, unknown products) and restore | P0 | Tested | `test_revenuecat_webhooks_and_restore` |
| M-004 | Web | Pricing page, plan card with manage or cancel, export and account deletion | P0 | Tested | e2e pricing.spec.ts (desktop + mobile) + axe; vitest billing helpers; `test_export_ownership_and_account_deletion` |
| A-001 | Admin | Roles and permissions, 404 for non-admins, command-line grant | P0 | Tested | `test_role_permissions_are_least_privilege`, `test_non_admins_see_nothing`, `test_grant_admin_command_line` |
| A-002 | Admin | Support tools with audit; no private content in responses; self-protection | P0 | Tested | `test_support_tools_are_audited_and_never_show_private_content` |
| A-003 | Admin | Metrics, revenue and AI cost estimates, content overview, audit pagination, roles | P0 | Tested | `test_superadmin_roles_audit_metrics_and_content`, `test_revenue_and_ai_cost_estimates`; e2e admin.spec.ts + axe |
| A-004 | Admin | Feature flags, translation management, privacy request queue, plan and content editing with review, MFA for admins, reporting store | P1 | Not Started | Needs review flows; MFA is a security phase item |
| E-001 | Enterprise | Organisations, roles (403 for members, 404 for non-members), join links with uses and expiry, seat limit, last-owner rules, audit, consent records | P0 | Tested | `test_create_invite_join_and_roles`, `test_seat_limit_and_licence_gives_premium` |
| E-002 | Enterprise | Voluntary programmes from versioned content; join and leave; participation removed on leaving | P0 | Tested | `test_programmes_are_voluntary` |
| E-003 | Enterprise | Suppressed group statistics from opted-in members only; no individual data in responses | P0 | Tested | `test_suppression_rules`, `test_analytics_only_from_opted_in_members_and_large_groups` |
| E-004 | Enterprise | Licence by superadmin (support can only look up) gives members the organisation plan; export; ownership handover on account deletion | P0 | Tested | `test_seat_limit_and_licence_gives_premium`, `test_export_and_account_deletion_hand_over_ownership` |
| E-005 | Web | Organisations list, join link page, organisation page with programmes, sharing choice, statistics, invitations, members and settings; admin Organisations tab | P0 | Tested | e2e organisations.spec.ts (desktop + mobile) + axe; vitest org helpers |
| E-006 | Enterprise | Self-serve organisation billing (per-seat checkout and invoices), SSO/SCIM, assigning programmes by team, member email invitations, statistics over time with differencing protection | P1 | Not Started | Needs the owner's pricing and a sales process; see ADR-023 consequences |
| M-005 | Monetization | One-off report purchases (credit model), live provider setup, tax, final prices, terms update, mobile purchase UI | P1 | Not Started | Needs the owner's Stripe, RevenueCat, Apple and Google accounts |

## Test results (latest local run, 2026-11-27)

| Suite | Command | Result |
| --- | --- | --- |
| Backend, SQLite | `pytest` | 207 passed |
| Backend, PostgreSQL 16 | `PDNA_TEST_DATABASE_URL=... pytest` | 207 passed |
| Coach evaluation (stand-in) | `python scripts/run_coach_eval.py` | all suites at threshold (32 cases) |
| Backend lint/types | `ruff check`, `ruff format --check`, `mypy app` (strict) | clean |
| Design tokens | `node --test` | 4 passed |
| Web unit | `vitest run` | 47 passed |
| Web types/lint/build | `tsc --noEmit`, `eslint .`, `next build` | clean, build succeeded |
| End-to-end + axe | `playwright test` (Chromium desktop + Pixel 7) | 44 passed |
