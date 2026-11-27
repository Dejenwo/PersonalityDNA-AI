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
| 5 | Authentication | Tested | Email/password accounts, verification, reset, rotating sessions, claim, history, export, deletion (ADR-010). No social login or MFA yet. |
| 6 | Assessment engine | Tested | Instruments, sessions, autosave, resume, deterministic scoring, versioning, audit. History is device-local until accounts exist. |
| 7 | Personality intelligence | In Progress | Big Five results, archetypes, trait explanations, strengths and growth. No shareable card or comparison yet. |
| 8 | AI coaching | Tested | Provider interface (stand-in + Anthropic), consented context from scores only, versioned prompt, crisis routing, input flags, streaming output guard, grounding check, encrypted messages, daily limits, usage records, evaluation suite, web chat (ADR-011). Live model not yet run: needs the owner's API key and spending cap. |
| 9 | Career intelligence | Tested | O*NET Interest Profiler Short Form (60 activities) as a **draft** instrument, count-based RIASEC scoring (engine 1.1.0), interest code with tie reporting, interest results page, career exploration page joining interests and Big Five working style, interests in coach context (ADR-012). Draft is hidden in production until the wording is checked against the official PDF and a lawyer confirms the CC BY-ND reading. |
| 10 | Relationship intelligence | Tested | One-time invitation links, consent from both people, one link per pair, comparison of Big Five bands with original similarity, difference, misunderstanding and prompt text, exercises and shared goals, revoke by either person, export and deletion (ADR-013). No compatibility score or prediction. |
| 11 | Leadership intelligence | Tested | Original 27-statement leadership preferences questionnaire (9 areas from the spec, labelled unvalidated), ranked results with build and stretch suggestions, 9 development modules with lessons, activities and reflection, activity progress for accounts, leadership preferences in coach context (ADR-014). Never presented as ability or used for employment decisions. |
| 12–25 | Emotional awareness onward | Not Started | See docs/PRODUCT_ROADMAP.md. |

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
| D-003 | Leadership | Module catalogue and detail (public), activity progress (accounts, idempotent), export, migration 0006 | P0 | Tested | `test_modules_and_progress` |
| D-004 | Coaching | Leadership preferences in coach context when results are shared | P0 | Tested | `test_history_and_coach_context` |
| D-005 | Web | Leadership results, leadership hub (suggested modules, all modules with progress), module pages with done toggles; shared latest-results hook | P0 | Tested | e2e leadership.spec.ts (desktop + mobile) + axe |
| D-006 | Leadership | Validation study, team or 360 views, manager programmes | P2 | Not Started | Needs a psychometrics reviewer; 360 views need a separate consent design and must never feed employment decisions |
| M-001 | Monetization | Entitlements service with plan config; Stripe and RevenueCat webhooks | P0 | Not Started | Needs accounts; live keys needed for real payments |

## Test results (latest local run, 2026-11-26)

| Suite | Command | Result |
| --- | --- | --- |
| Backend, SQLite | `pytest` | 152 passed |
| Backend, PostgreSQL 16 | `PDNA_TEST_DATABASE_URL=... pytest` | 152 passed |
| Coach evaluation (stand-in) | `python scripts/run_coach_eval.py` | all suites at threshold (32 cases) |
| Backend lint/types | `ruff check`, `ruff format --check`, `mypy app` (strict) | clean |
| Design tokens | `node --test` | 4 passed |
| Web unit | `vitest run` | 21 passed |
| Web types/lint/build | `tsc --noEmit`, `eslint .`, `next build` | clean, build succeeded |
| End-to-end + axe | `playwright test` (Chromium desktop + Pixel 7) | 28 passed |
