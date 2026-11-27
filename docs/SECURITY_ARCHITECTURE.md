# Security architecture

Frameworks: OWASP Top 10 (2021), OWASP API Security Top 10 (2023), OWASP MASVS for mobile, OWASP Top 10 for LLM applications, NIST SSDF. No compliance or certification is claimed.

## Implemented controls

| Control | Where | Test |
| --- | --- | --- |
| Object-level authorization (API1) | Every session/result lookup requires the matching token; 404 otherwise | `test_object_level_authorization`, `test_result_requires_owning_token` |
| Token storage | 256-bit random tokens, stored as SHA-256, constant-time compare, length cap | `test_token_stored_only_as_hash` |
| Input validation | Pydantic models with `extra=forbid`, size limits (≤500 answers, string lengths), range checks; DB check constraints | `test_invalid_answers_rejected` |
| Mass assignment | Explicit request models only | — |
| Rate limiting (API4) | Session creation per client IP | `test_session_creation_rate_limited` |
| Data exposure (API3) | Scoring keys never sent to clients; results only via token | `test_list_and_detail` |
| Security headers | API: nosniff, frame DENY, no-referrer, no-store. Web: CSP, frame-ancestors none, permissions policy | `test_health_and_security_headers` |
| CORS | Explicit origin allow-list | config |
| Inventory (API9) | API docs disabled in production | `test_docs_hidden_in_production` |
| Content integrity | Released content hash-locked | `test_editing_a_released_version_is_refused` |
| Least privilege containers | Non-root users in Dockerfiles | Dockerfiles |
| Secrets | Env vars only; `.env` git-ignored; gitleaks in CI | CI |
| Supply chain | Lockfiles, Dependabot, pip-audit and pnpm audit in CI | CI |
| Audit logging | Security and lifecycle events by id, without personal data; kept one year | service code; `test_retention_purges_only_what_has_expired` |
| Whole-API authorization sweep | Every operation in the OpenAPI document is called without credentials (must be 401 unless on the public list) and, signed in as a second person, with every id belonging to the first (must never succeed); no 5xx | `test_private_routes_need_sign_in`, `test_nobody_reaches_another_persons_records_by_id` |
| Logging privacy | Debug-level log capture across assessment, journal, goals, habits, coaching, search and login contains no private text or password | `test_private_content_never_reaches_logs` |
| Complete deletion | After account deletion no row in any table references the person | `test_every_table_with_personal_data_is_removed_with_the_account` |
| Security notices | Password change and refresh-token reuse produce an in-app notice and email that can't be turned off | `test_security_notices_for_password_change_and_stolen_sessions` |
| Retention | Daily purge of expired tokens and invitations, unfinished anonymous assessments (30 days), notifications (90 days), audit events (1 year) | `test_retention_purges_only_what_has_expired` |
| Production guards | Startup refuses weak JWT secret, dev outbox, insecure cookies, SQLite, missing encryption key, drafts, dev checkout, stand-in coach, wildcard or HTTP CORS origins, HTTP email links | `test_production_settings_guards`, `test_production_needs_https_origins_and_links` |
| Response headers (Phase 21) | API: `default-src 'none'` CSP, COOP, CORP (cross-origin only for public cards), permissions policy, HSTS in staging and production. Web: adds `object-src 'none'`, COOP and HSTS | `test_api_security_headers` |
| Raw HTML in the web app | Only constant JSON-LD; a unit test fails on any other use | vitest `security.test.ts` |

## Planned

Before launch (see docs/security/SECURITY_REVIEW_2026-11-27.md): independent penetration test; MFA option for accounts and required for admin roles; shared rate limiting (Redis or gateway) once more than one API instance runs; WAF at the edge; data encryption key in a KMS with rotation (today one key from `PDNA_DATA_ENCRYPTION_KEY`); log shipping with alerting on `user.refresh_reuse_detected` and repeated login failures. Already built since this section was first written: own accounts with rotating sessions (ADR-010), admin and organisation roles (ADR-022, ADR-023), field-level encryption for journals, coaching, goals and reports, signed and idempotent payment webhooks (ADR-021).
