# Incident response

1. **Detect**: alerts from error tracking (Sentry, planned), uptime checks, user reports.
2. **Triage** within 1 hour: severity 1 (data exposure, outage), 2 (major feature broken), 3 (minor).
3. **Contain**: revoke keys, disable affected feature flag, block abusive IPs, roll back.
4. **Investigate**: audit events, logs (no personal content), DB queries.
5. **Notify**: personal data breach → assess regulator notification (e.g. GDPR 72 hours) and user notification with counsel.
6. **Recover** and verify.
7. **Review**: blameless write-up within 5 working days; add tests or controls.

Contacts and on-call rotation: to be defined by the owner before beta.
