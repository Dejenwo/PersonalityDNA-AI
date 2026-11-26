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

## ADR-007: Authentication via Supabase Auth behind an interface (2026-11-26, planned)
**Context.** Spec names Supabase; no Supabase project or credentials exist yet.
**Decision.** Backend verifies JWTs through an `AuthProvider` interface. Production uses Supabase JWKS; development/tests use a local provider. Users table keyed by the auth provider's subject.
**Consequences.** Swapping providers is configuration. To be implemented in Phase 5.

## ADR-008: IPIP Big Five as the scientific foundation (2026-11-26)
**Decision.** Use the IPIP Big-Five Factor Markers (50 items) for the comprehensive assessment and the Mini-IPIP (20 items) for the quick one. Both are public domain (verified on ipip.ori.org).
**Consequences.** No licence fees. No population norms are shipped, so scores are shown on the response scale, not as percentiles.

## ADR-009: Web stack versions (2026-11-26)
**Decision.** Next.js 16.4, React 19.3, Tailwind 4.3, TypeScript 5.9 (TypeScript 7 not adopted yet for tooling compatibility). pnpm 10 workspaces.
