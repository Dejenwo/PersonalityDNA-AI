# Threat model

Method: STRIDE over the current data flows. Revisit at each phase that adds a data flow (auth, AI, payments, sharing, enterprise).

## Assets

Assessment answers and results (sensitive personal data), resume tokens, consent records, future: accounts, journals, coaching conversations, payment state.

## Data flows today

Browser ⇄ Web app (static/JS) ; Browser ⇄ API (JSON, `X-Session-Token`) ; API ⇄ PostgreSQL.

## Threats and mitigations

| ID | STRIDE | Threat | Mitigation | Status |
| --- | --- | --- | --- | --- |
| T1 | Spoofing | Guessing a session id to read results | Ids are UUIDv4 and the token is also required; 404 for both | Mitigated, tested |
| T2 | Spoofing | Brute-forcing tokens | 256-bit tokens; rate limiting on creation (add on reads with shared limiter) | Partly |
| T3 | Tampering | Changing answers after completion | 409 on closed sessions | Mitigated, tested |
| T4 | Tampering | Editing released instrument content | Hash lock at startup | Mitigated, tested |
| T5 | Repudiation | Disputed results | Stored engine/content/answers hashes; audit events | Mitigated |
| T6 | Info disclosure | Token leaks via logs/referrers | Token in fragment and header, never in query; `Referrer-Policy` | Mitigated |
| T7 | Info disclosure | Token theft via XSS (localStorage) | React escaping, strict CSP, no third-party scripts; move to httpOnly cookies with accounts | Partly |
| T8 | Info disclosure | DB leak exposes tokens | Only hashes stored | Mitigated |
| T9 | Info disclosure | Shared device: next user sees history | History shows only on that browser; "forget" control and account login planned | Open |
| T10 | DoS | Session creation spam | Per-IP limit; DB constraints | Partly (single instance) |
| T11 | DoS | Huge payloads | Request size limits via models; add proxy body limit | Partly |
| T12 | Elevation | Admin access to private content | No admin API yet; design forbids content access | Design |
| T13 | Info disclosure | Scoring keys reveal "right answers" | Keys never sent to clients | Mitigated |
| T14 | Info disclosure | Clickjacking | frame-ancestors none / X-Frame-Options DENY | Mitigated |

## Accounts (added with ADR-010)

| ID | STRIDE | Threat | Mitigation | Status |
| --- | --- | --- | --- | --- |
| T15 | Spoofing | Credential stuffing / brute force | Argon2id, per-IP and per-email limits, generic errors | Partly (single-instance limiter) |
| T16 | Info disclosure | Account enumeration | Register, resend and reset always 202; login errors identical; dummy hash timing | Mitigated, tested |
| T17 | Spoofing | Stolen refresh token | Rotation with reuse detection revokes the family; httpOnly cookie; path-scoped | Mitigated, tested |
| T18 | Tampering | CSRF on cookie refresh/logout | SameSite=Lax + required custom header (forces CORS preflight); logout only revokes | Mitigated |
| T19 | Spoofing | Old access token after password reset | Tokens with `iat` before `password_changed_at` rejected | Mitigated, tested |
| T20 | Info disclosure | Emailed token leakage | Tokens in URL fragment, single use, short expiry, stored hashed | Mitigated |
| T21 | Elevation | Claiming someone else's assessment | Requires that session's resume token; owned sessions can't be re-claimed | Mitigated, tested |
| T22 | Misconfiguration | Weak production secrets or dev email outbox in production | Settings validation refuses to start | Mitigated, tested |
| T23 | Information disclosure | A shared card reveals more than intended, or stays visible after the person changes their mind | Card holds only the chosen profile text and bands (no name, email or scores); token in the URL fragment; `no-store` and `noindex`; stopping sharing deletes the row; report and account deletion cascade | Mitigated, tested |
| T24 | Tampering | Script injection through card text in the SVG image | All text escaped; SVG served with `default-src 'none'`; card text comes only from versioned content | Mitigated, tested |
| T25 | Spoofing | Forged payment webhooks granting Premium | Stripe signature (HMAC-SHA256, 5-minute tolerance); RevenueCat shared secret compared in constant time; webhooks refuse to run unconfigured; plan must be a known paid plan | Mitigated, tested |
| T26 | Tampering | Replayed webhook events | Event ids stored once per provider (unique constraint) | Mitigated, tested |
| T27 | Elevation of privilege | A member or a narrow admin role reaching admin functions | Per-route permission checks; roles only by command line or superadmin; confirmed email required; 404 for missing permission; superadmin cannot remove their own role | Mitigated, tested |
| T28 | Information disclosure | Admins reading private journals, coaching or answers | No admin endpoint returns encrypted fields or content; tests assert private text never appears | Mitigated, tested |
| T29 | Information disclosure | An organisation re-identifying a member's results from group statistics | Only opted-in members counted; organisations can't see who opted in; group minimum 10; a trait shows only when every band has 3 or more; programme counts under 3 hidden; no individual endpoint | Mitigated, tested; differencing over time is a residual risk (ADR-023) |
| T30 | Elevation of privilege | A member or leaked join link gaining management rights or extra seats | Role checks per action (403 for members, 404 for non-members); admins can't invite admins or remove admins or owners; links hashed, limited uses and expiry, cancellable; seat limit checked under a row lock; always one owner | Mitigated, tested |

## Future flows to model

LLM providers (prompt injection, data leakage, cost abuse), payment webhooks (forgery, replay), relationship sharing (consent bypass), enterprise differencing over time (see T29), mobile (insecure storage, certificate pinning decision).
