# Incident response

**Status: ready to use once the owner names the on-call people and contacts below.**

## Contacts (owner to fill in before the beta)

| Role | Who | How to reach |
| --- | --- | --- |
| Incident lead (on call) | | |
| Backup | | |
| Legal and privacy adviser | | |
| Hosting, database and email providers | | Support links in the provider accounts |

## Severity

| Level | Examples | First response |
| --- | --- | --- |
| SEV1 | Personal data exposed or sent to the wrong person, data loss, the whole app down, crisis messages not handled | Within 1 hour, any time |
| SEV2 | A main flow broken (assessments, sign-in, results, payments), the coach giving unsafe replies | Within 4 hours, working days |
| SEV3 | A minor bug or a slow page | Next working day, through feedback triage |

## Steps

1. **Detect.** Uptime alerts on `/health/ready`, error spikes in logs, feedback marked as a problem, user email.
2. **Declare.** Open an incident note with the time, severity and incident lead. Every later step is recorded
   there with times.
3. **Contain.** Pick the smallest step that stops the harm:
   - Roll back to the previous images (docs/DEPLOYMENT_GUIDE.md); the database stays as it is.
   - Switch the coach off: `PDNA_COACH_ENABLED=false`, then restart.
   - Disable an account from the admin portal (it also signs the person out everywhere).
   - Rotate a leaked secret: provider keys at the provider; `PDNA_JWT_SECRET` signs everyone out. The data
     encryption key can't simply be replaced (K-15): get advice first.
   - Block abusive traffic at the platform's firewall.
4. **Investigate.** Use request ids (`X-Request-ID`, in every response and log line), the admin audit log and
   the database. Logs never contain answers, journals, coaching or feedback text, and should not be made to.
5. **Notify.** If personal data was exposed, involve the privacy adviser at once. Under GDPR the regulator must
   be told within 72 hours of becoming aware, and affected people without undue delay when the risk is high.
   App store and payment providers may also need to be told.
6. **Recover.** Fix forward or restore (docs/DISASTER_RECOVERY.md), run `scripts/smoke_test.py`, and watch for
   30 minutes.
7. **Review.** A blameless write-up within 5 working days: what happened, impact, timeline, root cause and
   actions. Every SEV1 and SEV2 gets a regression test or a control.

## Specific playbooks

- **Crisis content in feedback or support email.** Reply with the crisis resources on the help page and do not
  try to counsel. Tell the incident lead if the app's own crisis handling failed (SEV1).
- **Coach says something unsafe.** Switch the coach off, keep the conversation id (not its text) in the
  incident note, add the case to the evaluation suite (docs/AI_EVALUATION.md), fix, then switch it back on.
- **Suspected account takeover.** Disable the account, which signs it out everywhere, then contact the person
  at their registered email address.
- **Email not arriving.** Check the provider dashboard and the SPF, DKIM and DMARC records; people can still
  use the app, but can't confirm their email or reset passwords.
