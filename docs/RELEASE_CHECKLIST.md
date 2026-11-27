# Release checklist

Every item needs evidence (link to CI run, report or document). Nothing here is complete for a public release yet. The beta comes first: its plan and exit criteria are in docs/BETA_PROGRAM.md, and the reviewer packets are in docs/review/.

## Engineering
- [ ] All CI jobs green on the release commit
- [ ] Migrations tested against a copy of production data; backward compatible
- [ ] Load test meets PERFORMANCE_TESTING.md targets in staging
- [ ] Backup restore drill passed in the last 90 days
- [ ] Error tracking and alerts live

## Security and privacy
- [ ] Threat model updated for every new data flow
- [ ] External penetration test, criticals and highs fixed
- [ ] Privacy notice and terms reviewed by counsel; DPIA done
- [ ] Data export and account deletion verified end to end
- [ ] No secrets in repo history (gitleaks clean)

## Science and content
- [ ] Psychometrics reviewer signed off on wording and limitations
- [ ] No unsupported claims in app, store listing or marketing
- [ ] Licence record for every instrument

## AI
- [ ] AI evaluation suites pass (AI_EVALUATION.md)
- [ ] Spend caps and per-user limits active

## Product
- [ ] Accessibility: axe clean + manual screen reader pass (VoiceOver, TalkBack, NVDA)
- [ ] Payment sandbox tests for every purchase path
- [ ] Owner authorization recorded for deployment / publication

## Quality review board (MASTER_PROMPT.md §28)
- [ ] Evidence-based score ≥ 90/100 with no unresolved critical issues
