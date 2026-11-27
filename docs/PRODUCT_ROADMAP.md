# Product roadmap

Follows MASTER_PROMPT.md §24 (25 phases). Status is kept in DEVELOPMENT_PROGRESS.md; this file explains sequencing and what each phase depends on outside the codebase.

| Phase | Name | Depends on (external) | Order rationale |
| --- | --- | --- | --- |
| 1 | Product discovery | Owner for interviews, trademark search | Runs in parallel with engineering |
| 2 | Architecture | — | Done first, revised by ADRs |
| 3 | Repository foundation | GitHub Actions minutes | Done |
| 4 | Design system | Brand/icon decisions by owner | Tokens done; icon and mobile components next |
| 5 | Authentication | Supabase project (or self-hosted auth) for production | Local auth implementation first, behind an interface |
| 6 | Assessment engine | — | Done for Big Five |
| 7 | Personality intelligence | — | Share card, comparison after accounts |
| 8 | AI coaching | OpenAI/Anthropic API keys and spending limit | Mock provider and safety layer first |
| 9 | Career intelligence | O*NET Interest Profiler Short Form under CC BY-ND 4.0 (recorded); wording check and legal review before release | |
| 10 | Relationship intelligence | Done (PR #1) | Invitations, two-sided consent, band comparison, prompts and exercises, revoke |
| 11 | Leadership intelligence | Done | Original unvalidated preferences questionnaire, 9 modules, progress tracking (ADR-014) |
| 12 | Emotional awareness | Done (code); clinical safety review of wording and crisis resources per country before launch | Learning track with 7 modules, no score, support note, coach topic (ADR-015) |
| 13 | Growth academy | Done (code); content review by a learning designer before launch | 3 seven-day challenges, 30/60/90-day programmes from 12 weekly units, enrolment, daily progress, weekly self-checks (ADR-016) |
| 14 | Journaling and habits | Done (code); reminders wait for notifications | Encrypted journal (ADR-017); goals, milestones and habits without streaks (ADR-018) |
| 15 | Reports | Done (code) | Encrypted report snapshots with a reportlab PDF (ADR-019); opt-in, revocable share cards (ADR-020) |
| 16 | Monetization | Done (code), off by default; needs Stripe, RevenueCat, Apple and Google accounts to switch on | Plans as data, entitlement service, Stripe checkout and portal, RevenueCat webhooks and restore, pricing page (ADR-021) |
| 17 | Administration | Done (code); feature flags, translation and privacy-request tools later | Least-privilege roles, support tools, metrics with revenue and AI cost estimates, content versions, audit log, health (ADR-022) |
| 18 | Enterprise portal | Legal review of employer use | |
| 19 | Internationalization | Professional translators + psychometric review | |
| 20 | Growth infrastructure | Analytics vendor decision | |
| 21 | Security hardening | External penetration test (cost) | |
| 22 | Quality assurance | — | |
| 23 | Performance engineering | Staging environment | |
| 24 | Beta release | Owner authorization, hosting accounts | |
| 25 | Commercial launch | Owner authorization, app store review | |

Phases that need nothing external are done first. Phases that need credentials are built against interfaces with local or mock implementations, so only configuration is missing when credentials arrive.
