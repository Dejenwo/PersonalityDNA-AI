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

## Future flows to model

LLM providers (prompt injection, data leakage, cost abuse), payment webhooks (forgery, replay), relationship sharing (consent bypass), enterprise (re-identification from aggregates), mobile (insecure storage, certificate pinning decision).
