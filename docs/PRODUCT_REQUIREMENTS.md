# Product requirements

Source of truth for scope: MASTER_PROMPT.md. This document turns it into testable requirements and records what is built. Business figures in the master prompt are hypotheses, not facts.

## Product

PersonalityDNA AI helps adults understand their personality tendencies and turn that understanding into ongoing personal development: assessment, explanation, AI coaching, growth programs, and tools for careers, relationships and leadership.

## Users (launch: adults 18+)

Students, early-career and technology professionals, managers and founders, couples, career changers, coaches and organizations offering **voluntary** development programs. No under-18 users until legal and developmental safeguards exist.

## Principles (apply to every feature)

1. Scores are deterministic and documented. AI explains; it never scores.
2. No diagnostic, clinical, hiring or compatibility-prediction claims.
3. Supportive, balanced language: no trait level is better overall.
4. The user controls their data: consent first, export and deletion, no sale, no training on their data without separate consent.
5. Honest uncertainty: no fabricated percentiles, confidence or validation.

## Functional requirements by module

Status: ✅ implemented and tested · 🟡 partial · ⬜ not started.

| # | Module (master prompt §7) | Key requirements | Status |
| --- | --- | --- | --- |
| 1 | Discovery Center | Marketplace of assessments by tier (quick, comprehensive, advanced); intro, instructions, time estimate, source | 🟡 Big Five quick + comprehensive live; other modules not yet |
| 2 | Intelligence Engine | Versioned instruments, sessions, autosave, resume, deterministic scoring, audit, quality checks | ✅ |
| 3 | Big Five | Five domains, reverse keying, Emotional Stability with Negative Emotionality explained | ✅ |
| 4 | Archetypes | 16 original archetypes, primary + secondary, explanation of traits behind them, not types | ✅ (see PERSONALITY_ARCHETYPES.md) |
| 5 | Dashboard | Trait visualization, trait details, strengths, growth, history, comparison, share card | 🟡 results page + device history; no comparison or share card |
| 6 | AI Coach | Grounded on authorized results, distinguishes findings from suggestions, usage limits, safety layer | ⬜ |
| 7 | Agentic architecture | Insight, career, relationship, leadership, growth, retrieval agents behind one orchestrator | ⬜ |
| 8 | Career | RIASEC interests (licensed instrument), exploration, O*NET under its terms | ⬜ |
| 9 | Relationships | Mutual-consent sharing, similarities/differences, discussion prompts; no compatibility scores | ⬜ |
| 10 | Leadership | Leadership preferences, development exercises | ⬜ |
| 11 | Emotional awareness | Reflection and check-in activities; non-clinical; crisis resources | ⬜ |
| 12 | Development Academy | 7/30/60/90-day programs, daily exercises, milestones | ⬜ |
| 13 | Journal | Private journal, encrypted at rest, never visible to admins | ⬜ |
| 14 | Habits and goals | Habit tracking, goals, progress | ⬜ |
| 15 | Report Center | Comprehensive report, PDF, library | ⬜ |
| 16 | Social and referral | Share cards (user-initiated), referral links | ⬜ |
| 17 | Notifications | User-controlled reminders, localized | ⬜ |
| 18 | Monetization | Free/premium, report purchases, remotely configurable prices, Stripe (web), RevenueCat (mobile), server-side entitlements | ⬜ |
| 19 | Enterprise portal | Voluntary development programs, aggregate-only insights, no individual results without consent, no hiring use | ⬜ |
| 20 | Admin portal | Content/version management, analytics, privacy requests, audit; least privilege | ⬜ |

## Non-functional requirements

| Area | Requirement | Current evidence |
| --- | --- | --- |
| Accessibility | WCAG 2.2 AA | axe scans pass on all built screens; token contrast tests |
| Security | OWASP Top 10 / API Top 10 controls | See SECURITY_ARCHITECTURE.md and THREAT_MODEL.md |
| Privacy | Consent records, minimization, export, deletion | Consent records stored; export/deletion pending accounts |
| Reliability | Answers never lost on flaky networks | Autosave queue with retry and unload warning; e2e reload test |
| Determinism | Same answers + version → same scores | Unit and API tests |
| Performance | See PERFORMANCE_TESTING.md for SLO targets | Not yet load tested |
| i18n | English first; RTL-ready; reviewed translations only | Content model has locale; UI strings not yet extracted |

## Acceptance criteria for the first vertical slice (met)

- A visitor can choose an assessment, must confirm 18+ and consent before starting.
- Answers save automatically; reloading the page restores progress at the first unanswered statement.
- Finishing with missing answers is refused with the list of missing statements.
- Results show five trait scores with bands, primary and secondary archetype, strengths, growth ideas, methodology, limitations and references.
- Nobody without the session's private token can read the session or result.
