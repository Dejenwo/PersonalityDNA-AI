# Privacy requirements

Not legal advice. A qualified privacy lawyer must review before launch; no compliance with GDPR, UK GDPR, CCPA/CPRA or other laws is claimed.

## Data inventory (current)

| Data | Purpose | Basis (proposed) | Retention |
| --- | --- | --- | --- |
| Answers, timestamps | Score and show results | Consent | Anonymous: until user deletes, unfinished ones deleted after 30 days (`scripts/purge_expired.py`) |
| Results | Show results, history | Consent | As above |
| Consent records | Prove consent | Legal obligation | Life of data + statutory period |
| Client IP (in memory only, rate limiting) | Abuse prevention | Legitimate interest | Not persisted |
| Email, password hash, display name | Account | Contract | Until account deletion |
| Session tokens (hashed) | Keep users signed in | Contract | 30 days |
| Relationship invitations (token hash, type) and links (two user ids, type, consent ids) | Let two people compare trait bands | Consent from both people | Invitations: until accepted, cancelled or 7 days; links: until either person ends it or deletes their account |
| Learning activity progress (track, module and activity ids, time; leadership and emotional awareness) | Show progress through learning modules | Contract | Until unmarked or account deletion |
| Journal entries (title, text and tags encrypted; kind, date and optional mood in the clear) | The user's private journal; never shared, never shown to staff, never sent to AI providers | Contract | Until the user deletes them or the account |
| Personality reports (body encrypted; version, headline, kinds used and time in the clear) | Snapshot of the user's own results for reading and PDF download; never shared unless the user later creates a share card | Contract | Until the user deletes them or the account |
| Subscription references (provider, provider ids, plan, status, period end). Card details stay with Stripe, Apple or Google | Providing and verifying Premium | Contract | Until account deletion; providers keep their own financial records |
| Share cards (profile name and description and/or Big Five bands; never names, emails or scores) | Public card the user chose to share by link | Consent (the user's choice to share; withdrawn by stopping sharing) | Until the user stops sharing, deletes the report or the account |
| Goals, milestones and habits (titles and reasons encrypted; dates, status and done days in the clear) | Goal and habit tracking for the user only | Contract | Until the user deletes them or the account |
| Growth programme progress (programme, start and finish time, days done, weekly self-check ratings 1 to 5) | Show progress through programmes; ratings are for the user's own reflection and are not sent to AI providers | Contract | Until the user leaves or restarts the programme, or deletes the account |
| Referral code and acquisition tags (referrer, source, medium, campaign) | Show people how many joined with their link; count sign-ups by campaign | Legitimate interest (to review) | Until account deletion |
| Notifications and preferences (fixed-template text, never private content) | In-app notices, reminders and email choices | Contract; news by consent (opt-in) | Notifications 90 days; preferences until account deletion |
| Daily event counts (event name, day, count) | Understand which public pages are used | Not personal data | Aggregate only |

No device identifiers or third-party trackers are collected. Product analytics are daily counts with no identifier, and browsers sending Global Privacy Control or Do Not Track are not counted. First-touch campaign tags are kept in device storage for up to 30 days and sent only with registration; a lawyer should confirm this is strictly necessary, or it moves behind consent, before an EU launch (ADR-025).

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

## Administrative access (ADR-022)

Admin roles see account metadata (email, dates, status, plan, counts) and aggregates only. No admin endpoint returns journal text, coaching messages, assessment answers or report contents. Every admin change is audited with the admin's id and a reason.
