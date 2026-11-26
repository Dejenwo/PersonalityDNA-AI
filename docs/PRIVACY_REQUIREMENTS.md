# Privacy requirements

Not legal advice. A qualified privacy lawyer must review before launch; no compliance with GDPR, UK GDPR, CCPA/CPRA or other laws is claimed.

## Data inventory (current)

| Data | Purpose | Basis (proposed) | Retention |
| --- | --- | --- | --- |
| Answers, timestamps | Score and show results | Consent | Anonymous: until user deletes, incomplete purged after 30 days (job pending) |
| Results | Show results, history | Consent | As above |
| Consent records | Prove consent | Legal obligation | Life of data + statutory period |
| Client IP (in memory only, rate limiting) | Abuse prevention | Legitimate interest | Not persisted |
| Email, password hash, display name | Account | Contract | Until account deletion |
| Session tokens (hashed) | Keep users signed in | Contract | 30 days |
| Relationship invitations (token hash, type) and links (two user ids, type, consent ids) | Let two people compare trait bands | Consent from both people | Invitations: until accepted, cancelled or 7 days; links: until either person ends it or deletes their account |

No names, emails, device identifiers, analytics or third-party trackers are collected today.

## Requirements

1. Consent before any assessment data is stored; policy version recorded; re-consent when the version changes (implemented: 409 `consent_outdated`).
2. Adults only (18+ confirmation implemented); age assurance approach to be decided before mobile launch.
3. Data minimization: AI providers get scores, not answers (planned).
4. No sale of personal data; no training on user data without separate opt-in.
5. Rights: export (JSON) and deletion (hard delete; backups expire per DISASTER_RECOVERY.md) are implemented and tested. Correction: display name editable; email change not yet built. Consent withdrawal = account deletion for now.
6. Special category risk: personality and emotional-awareness data can be sensitive; treat as high-risk. Run a DPIA before launch.
7. Enterprise: employers never see individual results without that individual's explicit, revocable consent; aggregates need a minimum group size.
8. Cross-border transfers: document provider regions (Supabase, LLM providers) before launch.
9. Children: block under-18; no knowingly collected children's data.
10. Logs: no answers, journals or coaching text in logs (enforced by code review; add a log-scrubbing test with structured logging).
