# Beta programme

**Status:** ready to run once the owner chooses hosting and recruits testers. Nothing here has started.

The beta answers one question: is PersonalityDNA understandable, trustworthy and reliable for real people,
before anyone pays for it? It runs in two stages, then stops at clear exit criteria.

## Stages

| Stage | Who | Size | Length | Environment |
| --- | --- | --- | --- | --- |
| 1. Internal | The owner, friends and colleagues who agree to report problems | 5 to 10 people | 1 week | Staging, `NEXT_PUBLIC_BETA=true` |
| 2. External | Invited adults (18+) from the target audience | 30 to 100 people | 3 to 4 weeks | Production with beta flag, billing off |

Testers must be 18 or older (the app requires it). Do not recruit through employers or for any hiring purpose,
and do not offer the beta as a clinical or wellbeing service.

## Setup checklist

- [ ] Hosting, database backups and HTTPS in place (docs/DEPLOYMENT_GUIDE.md)
- [ ] Web built with `NEXT_PUBLIC_BETA=true`: every page shows a beta notice and a feedback link
- [ ] `PDNA_BILLING_ENFORCE=false`, so every feature is free during the beta; or give testers complimentary
      Premium from the admin portal
- [ ] Coach provider decided: the stand-in (free, clearly labelled demo mode) or the live model with the
      owner's API key, spending cap and the live evaluation run first (docs/AI_EVALUATION.md)
- [ ] Daily jobs scheduled: `scripts/send_reminders.py` and `scripts/purge_expired.py`
- [ ] A support account with the `support` role to read and triage feedback
- [ ] Error tracking and uptime alerts (docs/INCIDENT_RESPONSE.md)
- [ ] Invitation email to testers that says: it is a beta, data may be reset only with notice, how to send
      feedback, how to delete their account, and that it is not a clinical tool

## Internal test script (stage 1)

Each internal tester does every task on a phone and on a computer, then sends at least one piece of feedback
through the app. Note anything confusing, slow, broken or worrying.

1. Take Quick Discovery without an account; read the result; close the browser and resume another session.
2. Create an account, confirm the email, and keep the earlier result.
3. Take Comprehensive Discovery and compare the two results in history.
4. Read the leadership, careers, emotional awareness and growth sections; join a 7-day challenge.
5. Write two journal entries, search them, export them, delete one.
6. Set a goal with milestones and a habit; check in for a few days.
7. Make a report, download the PDF, create a share card, open its link signed out, then stop sharing.
8. Invite a second tester to compare; both accept; compare; then end the link.
9. Talk to the coach about your results (and check it refuses medical or diagnostic questions).
10. Create an organisation, invite a member, set up a programme.
11. Change notification settings, language and colour scheme; use the app with a keyboard only.
12. Export all your data, then delete the account and check you can't sign in.

The automated suites already cover these flows (tests/e2e); the script is about understanding and trust,
which tests can't judge.

## Feedback and triage

- People send feedback from the footer link or the beta notice on any page (`/feedback`). It records the
  kind (problem, idea, wording, accessibility, other), the message and the page path, never the query
  string. Signed-in senders choose whether support may contact them; otherwise support sees no account.
- Support reads it under **Admin → Feedback** and sets a status: new, planned, fixed or closed. The sender
  sees the status on the feedback page.
- Triage at least every working day during the beta:

| Severity | Examples | Response |
| --- | --- | --- |
| S1 critical | Data shown to the wrong person, data loss, crisis content mishandled, app unusable | Stop the beta if needed; fix within 24 hours; incident process (docs/INCIDENT_RESPONSE.md) |
| S2 major | A main flow fails, wrong result shown, accessibility blocker | Fix before the next release |
| S3 minor | Confusing wording, layout problem, small bug | Plan, batch into releases |
| Idea | New feature or change | Record in docs/PRODUCT_ROADMAP.md if accepted |

Every S1 and S2 gets a regression test before it is closed. Feedback is deleted after a year.

## What we measure

Only what the app already records, with no tracking of individuals:

- Daily event counts (assessment started and completed, report created and so on) from the admin metrics.
- Feedback counts by kind and status.
- Short interviews with 5 to 10 testers at the end of stage 2 (with their permission; notes kept without
  names).

## Exit criteria (to move to launch)

- [ ] No open S1 or S2 defects
- [ ] Every main flow completed by at least 10 external testers without help
- [ ] Manual screen-reader pass (VoiceOver and NVDA or TalkBack) with no blockers
- [ ] Scientific review signed off (docs/review/SCIENTIFIC_REVIEW_PACKET.md)
- [ ] Legal review signed off (docs/review/LEGAL_REVIEW_PACKET.md)
- [ ] Clinical safety review of the coach and emotional-awareness wording (K-14)
- [ ] Staging load test meets the targets in docs/PERFORMANCE_TESTING.md
- [ ] Live coach evaluation passed, if the live model will be used at launch
