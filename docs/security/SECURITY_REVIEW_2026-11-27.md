# Security and privacy review, Phase 21 (2026-11-27)

An internal review done while building. It is **not** an independent penetration test or a legal opinion. Both are still needed before launch (see "Before launch").

## Scope

- The API (`services/backend`) and the web app (`apps/web`), on branch `phase-21-security`.
- All data flows listed in docs/THREAT_MODEL.md.
- Mobile apps, hosting and the production network are out of scope because none of them exist yet.

## What was tested

| Area | Method | Result |
| --- | --- | --- |
| Authentication on every route | Every operation in the OpenAPI document called without credentials | All private operations answer 401; 26 public operations are on an explicit list; no 5xx |
| Object-level authorization | A second account calls every operation that takes an id, using every id belonging to a first account that has results, a report, a share card, a journal entry, a goal, a habit, a programme, a coaching conversation, a relationship invitation and an organisation | No operation succeeded; no 5xx. Write routes with required bodies answer 422 first, so per-domain tests cover them |
| Logging | Debug-level capture through assessment, journal, goals, habits, coaching, journal search and login | No private text or password in logs |
| Deletion | Account deletion, then a scan of every column that references `users` | No rows left |
| Validation errors | Error responses checked for echoed input | Errors give field locations and messages, not submitted values |
| Sessions | Refresh-token replay and password reset | All sessions end; the owner gets a security notice by email and in the app |
| Headers | API and web response headers | CSP, COOP, CORP, permissions policy, nosniff and frame denial on every response; HSTS behind TLS |
| Production configuration | Settings validation | Refuses insecure secrets, cookies, database, email outbox, drafts, dev checkout, stand-in coach, wildcard or HTTP origins and HTTP email links |
| Dependencies | `pip-audit .` (project dependencies resolved in isolation), `pnpm audit --prod` | No known vulnerabilities |
| Static analysis | `bandit -r app` plus ruff `S` rules in CI | No high findings. One medium (`urlopen`) is guarded by an HTTPS-only check. Low findings are type-narrowing asserts and output escaping, which are false positives |
| Secrets | gitleaks in CI; `.env` ignored | No secrets in the repository |

## Remediations in this phase

1. **Security notices.** Password changes and stolen-session detection had no user-facing signal. Both now send a notice that can't be turned off (T33).
2. **Retention job.** Retention periods for unfinished anonymous assessments, tokens, invitations and the audit log were documented but not enforced. `scripts/purge_expired.py` now enforces them (T34).
3. **API headers.** API responses lacked a CSP, COOP, CORP and HSTS. All are added.
4. **Web headers.** The web CSP lacked `object-src 'none'`, and the web app lacked COOP and HSTS. All are added.
5. **Production startup.** Production could start with wildcard or HTTP CORS origins, or HTTP links in emails. Startup now refuses both.
6. **Referral counts.** Phase 20 referral stats would have shown referrers how many friends pay, which with small numbers reveals a named friend's billing. That count was removed before release.
7. **Regression protection.** New endpoints are now covered automatically by the whole-API sweeps (T35).

## Privacy verification

Checked against docs/PRIVACY_REQUIREMENTS.md.

| Requirement | Evidence |
| --- | --- |
| 1. Consent before storing assessment data, re-consent on policy change | `test_consent_and_age_required`, `test_status_and_consent_required`, 409 `consent_outdated` tests in tests/test_auth.py |
| 2. Adults only | Age confirmation required at registration and assessment start (same tests). Age assurance for mobile is still open |
| 3. AI providers get scores, not answers | `test_context_contains_scores_not_answers_or_identity` |
| 4. No sale of data, no training without opt-in | No data leaves except to the configured email, billing and (when enabled) LLM providers. Analytics are counts with no identifiers (`test_anonymous_event_counts`) |
| 5. Export and deletion | `test_export_and_delete_account`, `test_every_table_with_personal_data_is_removed_with_the_account`, per-domain export tests |
| 6. Sensitive data treated as high risk | Field-level encryption for journals, coaching, goals and reports (`test_entries_are_encrypted_and_private`). A DPIA is still to be done |
| 7. Employers never see individual results | `test_analytics_only_from_opted_in_members_and_large_groups`, `test_suppression_rules` |
| 8. Cross-border transfers | Not verifiable until hosting and providers are chosen |
| 9. No children's data | 18+ confirmation (see 2) |
| 10. No private text in logs | `test_private_content_never_reaches_logs` |
| Staff can't read private content | `test_support_tools_are_audited_and_never_show_private_content` |
| Notifications never quote private content | `test_daily_reminders_are_generic_and_sent_once` |

## Residual risks

- **Group statistics:** differencing over time can still narrow down individuals (T29, ADR-023).
- **Rate limiting:** limits are in memory and per instance, so they weaken once the API runs more than one instance.
- **Encryption key:** a single data encryption key comes from the environment. There is no KMS and no rotation yet.
- **No MFA:** admin roles rely on a password and email alone.
- **Inline scripts:** the CSP allows inline scripts (ADR-026). The app renders no user HTML, and a test enforces this.
- **Attribution tags:** storing first-touch tags on the device needs a legal view for the EU (ADR-025).

## Before launch

These are owner or vendor actions. They are tracked as S-004 in DEVELOPMENT_PROGRESS.md.

1. **Penetration test:** an independent test against staging, with findings fixed or accepted in writing.
2. **MFA:** offered to everyone, and required for admin roles.
3. **Key management:** the data encryption key held in a KMS, with a rotation procedure and re-encryption job.
4. **Shared rate limiting:** Redis or the API gateway, plus a WAF at the edge.
5. **Logging and alerts:** central logging with alerts on `user.refresh_reuse_detected`, bursts of `user.login_failed` and admin role changes.
6. **Daily jobs:** `scripts/send_reminders.py` and `scripts/purge_expired.py` scheduled in production.
7. **Legal and privacy:** a DPIA, records of processing, and provider regions documented. A lawyer reviews the privacy notice, terms and the attribution storage question.
