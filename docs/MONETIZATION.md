# Monetization

**Status: design. Pricing below is the owner's hypothesis from MASTER_PROMPT.md, to be tested; nothing is implemented.**

## Plans (remotely configurable)

| Plan | Price hypothesis | Includes |
| --- | --- | --- |
| Free | $0 | Quick + comprehensive Big Five, results, archetypes, share card, limited daily AI coaching |
| Premium monthly | $9.99 | Comprehensive report and PDF, expanded coaching, career/leadership/relationship modules, growth programs, analytics |
| Premium annual | $69.99 | Same |
| One-off reports | $9.99–$19.99 | Comprehensive, career, relationship, leadership reports |
| Enterprise | Custom | Voluntary development programs, aggregate insights |

## Architecture

- `entitlements` service is the only thing features check ("can this user use X?"). Providers feed it.
- Web: Stripe Checkout + webhooks (signature-verified, idempotent by event id).
- Mobile: Apple IAP and Google Play Billing via RevenueCat; RevenueCat webhooks update entitlements. Digital goods on iOS/Android go through store billing per current store rules.
- Prices and plan contents in a `plans`/`prices` table editable from the admin portal, not in code.
- AI usage allowances per plan; no unlimited lifetime AI.

## Ethics

No dark patterns: clear prices, easy cancellation, no fake urgency, no pre-checked upsells, free tier remains genuinely useful.

## External dependencies

Stripe account, RevenueCat account, Apple Developer Program ($99/yr) and Google Play Console ($25 one-time). All need the owner.
