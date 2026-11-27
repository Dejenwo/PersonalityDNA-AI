# Architecture decision records

Each ADR: context, decision, consequences. New decisions are appended; superseded ones are marked, not deleted.

## ADR-001: Governing specification (2026-11-26)
**Context.** The owner supplied two master prompts; the second (Option C, full commercial platform) replaces the first.
**Decision.** MASTER_PROMPT.md holds the second prompt verbatim and governs scope. The repository is `Dejenwo/PersonalityDNA-AI` (the prompt's `personality-dna-ai` name is superseded by the owner's actual repository).
**Consequences.** Work proceeds through the 25 phases; items needing credentials or authorization are built against interfaces.

## ADR-002: Modular monolith backend in Python/FastAPI (2026-11-26)
**Context.** Spec requires Python/FastAPI and warns against premature microservices.
**Decision.** One FastAPI service with domain packages. Domains talk through Python interfaces, not HTTP.
**Consequences.** Simple deployment and transactions. Boundaries must be kept by convention and review.

## ADR-003: Assessment content as immutable, versioned files (2026-11-26)
**Context.** Scores must be reproducible and auditable; content needs review history.
**Decision.** JSON files in `assessment-content/`, schema-validated at startup, SHA-256 hashed and registered in `assessment_versions`. A changed hash for an existing id+version stops the app from starting.
**Consequences.** Git is the review trail. Admin-portal editing (Phase 17) must create new versions, never edit released ones.

## ADR-004: Deterministic scoring engine, separate from AI (2026-11-26)
**Context.** Spec: "AI must never replace the deterministic assessment scoring engine."
**Decision.** Pure functions with Decimal arithmetic and ROUND_HALF_UP. Results store engine version, instrument version, content hash and answers hash.
**Consequences.** Any formula change requires a new `ENGINE_VERSION`; old results stay explainable.

## ADR-005: Anonymous-first assessment sessions with resume tokens (2026-11-26)
**Context.** Accounts are not built yet; a sign-up wall before the first test hurts conversion and collects data early.
**Decision.** Creating a session returns a 256-bit random token, shown once; only its SHA-256 is stored. Every session/result request needs it. Wrong or missing tokens get 404.
**Consequences.** Losing the token loses access (acceptable for anonymous use; accounts will fix this). Tokens never appear in server logs because the web app passes them in the URL fragment and the `X-Session-Token` header.

## ADR-006: OpenAPI-generated TypeScript client (2026-11-26)
**Decision.** `scripts/export_openapi.py` writes `packages/api-client/openapi.json`; `openapi-typescript` generates types. CI checks both are current.
**Consequences.** Web and mobile share one typed client; API changes surface as type errors.

## ADR-007: Authentication via Supabase Auth behind an interface (2026-11-26) — superseded by ADR-010
**Context.** Spec names Supabase; no Supabase project or credentials exist yet.
**Decision.** Backend verifies JWTs through an `AuthProvider` interface. Production uses Supabase JWKS; development/tests use a local provider. Users table keyed by the auth provider's subject.
**Consequences.** Swapping providers is configuration. To be implemented in Phase 5.

## ADR-008: IPIP Big Five as the scientific foundation (2026-11-26)
**Decision.** Use the IPIP Big-Five Factor Markers (50 items) for the comprehensive assessment and the Mini-IPIP (20 items) for the quick one. Both are public domain (verified on ipip.ori.org).
**Consequences.** No licence fees. No population norms are shipped, so scores are shown on the response scale, not as percentiles.

## ADR-009: Web stack versions (2026-11-26)
**Decision.** Next.js 16.4, React 19.3, Tailwind 4.3, TypeScript 5.9 (TypeScript 7 not adopted yet for tooling compatibility). pnpm 10 workspaces.

## ADR-010: Built-in email/password accounts; Supabase Auth optional later (2026-11-26)
**Context.** No Supabase project or credentials exist, and the owner asked for continuous progress. Waiting would block accounts, history, export and deletion.
**Decision.** The backend owns accounts: Argon2id password hashes, emailed single-use tokens (verification, reset) stored hashed, 15-minute HS256 access tokens, 30-day rotating refresh tokens with reuse detection (family revocation). Web keeps the access token in memory and the refresh token in an httpOnly, SameSite=Lax cookie scoped to `/api/v1/auth`; cookie refresh requires the `X-PDNA-CSRF` header. Mobile receives the refresh token in the body for secure storage. Email goes through an `EmailSender` interface (in-memory outbox in development, SMTP in production).
**Consequences.** Works today on any PostgreSQL, including Supabase's database. Social login, MFA and magic links are not built; if the owner later prefers Supabase Auth, the access-token check is the only seam to swap (JWKS verification) and users can be migrated by email. Startup refuses unsafe production settings (missing JWT secret, dev outbox, insecure cookie, SQLite).

## ADR-011: AI coach as one guarded provider call per turn (2026-11-26)
**Context.** Phase 8 needs a coach before any AI provider key exists, and the spec requires provider abstraction, safety controls, usage limits and evaluation. Multi-agent orchestration is allowed only when it measurably helps.
**Decision.** One streamed provider call per turn behind an `LLMProvider` interface. Implementations: a deterministic stand-in (`mock`, the default; clearly labelled "demo mode" to users) and Anthropic (`claude-opus-5-5` via the official SDK, effort configurable, shared instructions cached, personal context never in the cached block). Context is built server-side from the conversation owner's consented result: scores, bands, archetype and quality flags, never answers or identity. Around the call: rule-based crisis routing before the model (never limited, never sent to the model), input flags, a streaming output guard that stops generation and retracts the reply on diagnosis, professional, percentile, prediction or prompt-leak violations, refusal handling and a grounding check. Message text is encrypted at rest with AES-256-GCM bound to the row id. A rolling 24-hour limit counts usage records, which survive conversation deletion. An OpenAI provider is not built until the owner wants a second provider.
**Consequences.** The whole feature runs and is tested without keys; adding the key switches it on (`PDNA_COACH_PROVIDER=anthropic`). Rules are a backstop with known limits (English only, phrase based), so the model-level evaluation suite must pass before launch. The one-reply-at-a-time guard is per process (see KNOWN_ISSUES K-12).

## ADR-012: Career interests as a second assessment family (2026-11-26)
**Context.** Phase 9 needs a RIASEC interest measure that is free to use commercially. The O*NET Interest Profiler Short Form is published by USDOL/ETA under CC BY-ND 4.0, which allows commercial use with attribution but no derivatives. Its wording could not be checked against the official PDF from the development sandbox.
**Decision.** Instruments gain `family` (`big_five`, `interests`), `scoring` (`likert_mean`, `count_endorsed`) and `status` (`released`, `draft`), all defaulting so existing file hashes do not change. The Short Form is stored unmodified as a draft: drafts load only when `PDNA_CONTENT_INCLUDE_DRAFTS` is on (default in development and test, refused in production), may change until first released, and are immutable afterwards. Scoring counts liked activities per area (engine 1.1.0); the interest code is the top three areas with Holland order as a deterministic tie break, and ties across third place are shown rather than hidden. Results store an `interest_profile` and no archetypes. The coach receives the latest interest result next to the Big Five result when the user shares results. Occupation matching is left to O*NET's own sites (My Next Move, O*NET OnLine) rather than an in-app job list.
**Consequences.** No in-app claim links interests or personality to job suitability. Before release the owner must have the wording verified against the official PDF and the licence reading confirmed by a lawyer (KNOWN_ISSUES K-16). An in-app occupation search needs O*NET Web Services registration.

## ADR-013: Relationship comparisons from bands, by invitation link (2026-11-26)
**Context.** Phase 10 compares two people's personalities with consent from both, revocable at any time, without compatibility percentages or predictions, and without exposing journals or coaching.
**Decision.** An inviter creates a one-time link (random token in the URL fragment, SHA-256 stored, 7-day expiry, at most 10 open) after recording `relationship_sharing` consent. The invitee must be signed in and verified, sees who is inviting, and records their own consent to accept. Accepting deletes the invitation and creates one link per pair of people. The comparison is computed on each request from each person's latest Big Five result and shows only bands (lower, middle, higher), matched to original text: same band is "similar", lower against higher is "different", middle against either is "some difference". There is no overall score. Either person can delete the link, which removes it for both. Invitations are shared by the user (copy link) rather than emailed by us, so we never handle a third party's address.
**Consequences.** Nothing about the other person is stored or exported beyond the link itself. A newer result changes the comparison automatically; a person who has no Big Five result sees a prompt to take one. The coach does not receive the other person's data. The relationship text is original and unvalidated (ORIGINAL_CONTENT.md).

## ADR-014: Leadership preferences as an original, unvalidated reflection questionnaire (2026-11-27)
**Context.** Phase 11 asks for leadership preference assessments across nine areas (strategic, collaborative, coaching, delegation, decisions, communication, conflict, team development, planning). No free, commercially usable validated instrument covering these areas was identified, and the project must not invent scientific claims.
**Decision.** A third instrument family, `leadership`, with an original 27-statement questionnaire (three per area, interleaved, 1–5 enjoyment scale) scored by the existing Likert engine (no engine change). Results rank areas against each other only: no bands, norms or percentiles; ties keep content order; a spread under 10 points is called even. The result suggests one module to build on the top preference and two for the least preferred areas. Nine original modules hold lessons, activities and a reflection question; signed-in users can mark activities done (content ids only). Every surface states that this is unvalidated, describes preferences not abilities, and must never be used to select, promote or rate anyone.
**Consequences.** Released content is immutable, so wording changes after review become version 1.1.0. A validation study needs a psychometrics reviewer before any stronger claim.

## ADR-015: Emotional awareness as a learning track with no score (2026-11-27)
**Context.** Phase 12 asks for emotional awareness learning (self-awareness, empathy, reflective communication, active listening, stress reflection, interpersonal understanding, constructive expression). Free emotional intelligence tests suitable for commercial use with norms were not identified, emotional intelligence scores invite clinical and hiring misuse, and the spec forbids therapy claims.
**Decision.** No emotional awareness questionnaire and no score. The phase ships an original learning track of seven modules (one per area), each with two short lessons, two everyday activities and a reflection question, plus a support note pointing to emergency services, 988 in the US and findahelpline.com. Leadership modules and emotional awareness modules now share one model: a learning track (`LearningTrack`) served at `/api/v1/learning/{track}/modules`, with progress in `learning_activity_progress` keyed by track (migration 0007 moves existing leadership progress across). The coach gets an "Emotions and communication" topic whose instructions repeat the not-therapy, no-diagnosis, no-rating rules. The web app groups tracks under a Learn page.
**Consequences.** New tracks (for example the growth academy in Phase 13) are content files plus one line in `ContentBundle.track`. The `/api/v1/leadership/*` routes from Phase 11 were replaced before any client outside this repository used them. A clinical safety reviewer should read the wording and the support note, and crisis resources need per-country entries before launch outside the US.
