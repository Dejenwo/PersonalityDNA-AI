# Legal and compliance review packet

For a lawyer qualified in privacy, consumer and software law for the launch markets the owner chooses. This
lists what exists and what is missing. It is not legal advice and nothing here has been reviewed.

## Missing documents (must be written by or with counsel)

- **Terms of service.** None exist yet. Registration currently asks only for agreement to the privacy
  notice. Terms are needed for accounts, subscriptions, organisations and the beta.
- **Subscription terms**: renewal, cancellation, refunds, withdrawal rights, taxes (docs/MONETIZATION.md).
- **Data processing agreement** for organisations that buy seat licences.
- **Data protection impact assessment** (personality data, AI coaching, organisations).
- **Beta tester terms**, if counsel thinks the general terms are not enough.

## Please review

| # | Topic | Where | Questions |
| --- | --- | --- | --- |
| 1 | Privacy notice and consent wording, policy version `2026-11-26` | `apps/web/src/app/privacy/page.tsx`, `services/backend/app/security/consent.py`, `docs/PRIVACY_REQUIREMENTS.md` | Is the notice complete and accurate for each launch market? Is personality data special-category data where we launch? |
| 2 | Age limit (18+, self-declared) | registration and assessment start | Is self-declaration enough? |
| 3 | Data inventory, retention periods and the daily purge | `docs/PRIVACY_REQUIREMENTS.md`, `services/backend/app/security/retention.py` | Are retention periods justified? |
| 4 | Export and account deletion | `/api/v1/privacy/export`, account page | Does this meet access, portability and erasure rights? |
| 5 | AI coach: consent, what is sent to the provider, disclosures, crisis routing | `docs/AI_ARCHITECTURE.md`, `docs/AI_SAFETY.md`, coach consent screen | Is the consent valid? Is the provider a processor with suitable terms? Are crisis resources correct for each market? |
| 6 | First-touch referral and campaign tags kept on the device | ADR-025 | Strictly necessary, or does it need a consent banner in the EU and UK? |
| 7 | Product analytics: daily counts only, honours GPC and Do Not Track | ADR-025 | Any consent needed? |
| 8 | Relationships: two-person consent and comparison | ADR-013 | Is the consent flow adequate? |
| 9 | Organisations: voluntary membership, group statistics only (10+ members, bands of at least 3) | ADR-023 | Employment-context risks: is the "not for hiring or performance decisions" safeguard enough? |
| 10 | Assessment licences: IPIP (public domain), O*NET (CC BY-ND 4.0), original content | `assessment-content/licenses/` | Is the CC BY-ND reading right for the way the form is presented (K-16)? |
| 11 | Marketing and claims: no validation, accuracy or outcome claims | home page, pricing, `docs/MARKETING_STRATEGY.md` | Anything that could be read as a health claim or misleading? |
| 12 | Payments: Stripe, Apple and Google in-app purchases, RevenueCat | `docs/MONETIZATION.md` | Store rules and consumer law for subscriptions |
| 13 | Feedback: messages people send, kept a year, support sees the account only with permission | ADR-028 | Notice and retention adequate? |
| 14 | Name and trademark "PersonalityDNA" | — | Clearance in launch markets |
| 15 | Accessibility obligations | `docs/QA_REPORT_2026-11-27.md` | Which standards apply (for example the European Accessibility Act)? |

## Sign-off

| Reviewer | Jurisdictions | Date | Decision |
| --- | --- | --- | --- |
| | | | |
