# Known issues and open items

## Blockers needing the owner

| Item | Why it's needed | Phase |
| --- | --- | --- |
| Supabase project (or decision to self-host auth) | Production accounts | 5 |
| Anthropic API key, spending cap and data-retention choice | Real AI coaching and the live evaluation run (the stand-in works without) | 8 |
| Stripe, RevenueCat, Apple and Google developer accounts | Payments, app stores | 16, 25 |
| Trademark search for "PersonalityDNA" and archetype names | Brand risk | 1 |
| Independent psychometrics reviewer | Any scientific claim, wording review | 1, 24 |
| Privacy lawyer review, DPIA | Launch | 21–24 |
| Brand mark and app icon direction | Design system | 4 |
| Check the O*NET Interest Profiler wording against the official PDF, and a lawyer's confirmation of the CC BY-ND 4.0 reading | Releasing the career interest assessment (it stays a hidden draft in production until then) | 9 |

## Technical issues

| ID | Issue | Impact | Plan |
| --- | --- | --- | --- |
| K-1 | Rate limiter is in-process | Not effective across multiple instances | Redis or gateway limiter before scaling out |
| K-2 | Device resume tokens in localStorage (account sessions use httpOnly cookies) | Exposed if an XSS bug ever exists | Strict CSP; tokens only unlock that one assessment |
| K-3 | No purge job for abandoned anonymous sessions, expired auth/refresh tokens, unverified accounts | Data kept longer than needed | Background job runner (next infrastructure task) |
| K-4 | Docker images not built in the development sandbox (Docker Hub rate limit / proxy) | Dockerfiles unverified | Verify in CI or locally |
| K-5 | CI workflow not yet observed running on GitHub | Possible environment differences | Check first run on the PR |
| K-6 | UI strings not extracted for i18n | Translation needs refactor | Phase 19, start extracting with mobile |
| K-7 | "Forget this assessment" control missing on shared devices | Privacy on shared computers | Add with history improvements |
| K-8 | CSP allows 'unsafe-inline' scripts (Next.js bootstrap) | Weaker XSS defence | Nonce-based CSP via middleware |
| K-9 | Email is sent in-process after the response (FastAPI background task) | A crash can drop an email; user can request again | Move to a job queue with retries |
| K-10 | No breached-password check | Weak but uncommon passwords accepted | Add k-anonymity breach check (needs approval to call an external service) |
| K-11 | No MFA or social login | Lower account security options | Phase 21 / app store requirements |
| K-12 | Coach "one reply at a time" guard and rate limiter are per process | Two instances could stream into one conversation at once (the database unique sequence still prevents corruption) | Shared lock (Redis/Postgres advisory lock) before scaling out |
| K-13 | Crisis and output rules are English, phrase-based | Misses paraphrases and other languages; the model prompt is the main defence | Live evaluation, model-based classifier, localized rules with i18n |
| K-14 | Coach prompt and safety wording not yet reviewed by a clinician or lawyer | Crisis resources and disclaimers need professional review | Owner to arrange review before launch |
| K-15 | Data-encryption key rotation not automated | Re-encryption needed if the key is replaced | Versioned ciphertext prefix (`v1:`) is in place; add rotation job |
| K-16 | O*NET Interest Profiler Short Form is a draft: item wording, order and area keys were entered without access to the official PDF (site blocked from the sandbox) | Not shown in production; results labelled Preview | Verify against https://www.onetcenter.org/dl_tools/ipsf/Interest_Profiler.pdf, then set `status` to `released` |
| K-17 | Signed out, every page load asks the API to restore a session, which answers 401 | Harmless, but shows as a failed request in the browser console and adds one API call per visit | Keep; or add a non-secret "may be signed in" hint so visitors skip the call (needs a privacy check) |
| K-18 | No terms of service yet; registration asks only for agreement to the privacy notice | Accounts, subscriptions and organisations have no contract terms | Counsel to draft (docs/review/LEGAL_REVIEW_PACKET.md) |
| K-19 | No error-tracking service; investigation relies on logs and request ids | Errors are found by log searches and alerts, not grouped automatically | Owner to choose a provider; scrub personal data before sending (ADR-029) |
