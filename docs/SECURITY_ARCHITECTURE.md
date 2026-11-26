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
| Audit logging | Session created/completed events without personal data | service code |

## Planned

Auth (Supabase JWT verification, MFA option), RBAC for admin and enterprise roles, field-level encryption for journals and coaching messages (envelope encryption, keys in a KMS), webhook signature verification and idempotency for payments, shared rate limiting (Redis/gateway), WAF at the edge, CSP nonces, SAST beyond ruff security rules, penetration test before launch.
