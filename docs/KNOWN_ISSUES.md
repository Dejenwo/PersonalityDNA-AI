# Known issues and open items

## Blockers needing the owner

| Item | Why it's needed | Phase |
| --- | --- | --- |
| Supabase project (or decision to self-host auth) | Production accounts | 5 |
| Anthropic and/or OpenAI API keys + spending cap | Real AI coaching (mock provider works without) | 8 |
| Stripe, RevenueCat, Apple and Google developer accounts | Payments, app stores | 16, 25 |
| Trademark search for "PersonalityDNA" and archetype names | Brand risk | 1 |
| Independent psychometrics reviewer | Any scientific claim, wording review | 1, 24 |
| Privacy lawyer review, DPIA | Launch | 21–24 |
| Brand mark and app icon direction | Design system | 4 |

## Technical issues

| ID | Issue | Impact | Plan |
| --- | --- | --- | --- |
| K-1 | Rate limiter is in-process | Not effective across multiple instances | Redis or gateway limiter before scaling out |
| K-2 | Resume tokens in localStorage | Exposed if an XSS bug ever exists | Strict CSP now; httpOnly cookie sessions with accounts |
| K-3 | No purge job for abandoned anonymous sessions | Data kept longer than needed | Scheduled job in Phase 5 |
| K-4 | Docker images not built in the development sandbox (Docker Hub rate limit / proxy) | Dockerfiles unverified | Verify in CI or locally |
| K-5 | CI workflow not yet observed running on GitHub | Possible environment differences | Check first run on the PR |
| K-6 | UI strings not extracted for i18n | Translation needs refactor | Phase 19, start extracting with mobile |
| K-7 | "Forget this assessment" control missing on shared devices | Privacy on shared computers | Add with history improvements |
| K-8 | CSP allows 'unsafe-inline' scripts (Next.js bootstrap) | Weaker XSS defence | Nonce-based CSP via middleware |
