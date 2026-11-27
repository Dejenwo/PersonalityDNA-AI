# Monetization

**Status: built and tested with stand-ins; off by default.** `PDNA_BILLING_ENFORCE=false` keeps every feature available until the owner has created the Stripe and RevenueCat accounts, products and prices. Prices are the owner's hypothesis from MASTER_PROMPT.md and need market validation.

## Plans (`services/backend/app/billing/plans.v1.json`)

| Plan | Price | Includes |
| --- | --- | --- |
| Free | $0 | Assessments and results, profile and archetype, reports and a share card, interest and leadership questionnaires, 7-day challenges, journal, goals and habits, 5 coaching messages a day |
| Premium monthly | $9.99 a month | Free, plus PDF reports, 30/60/90-day programmes, relationship comparisons, 30 coaching messages a day |
| Premium annual | $69.99 a year | Same as monthly |
| One-off reports | $9.99–$19.99 | Not built yet (needs a credit model; tracked as M-005) |
| Organisation licence | Custom, per seat | Recorded by a superadmin (seats and length); members get Premium features while it is active. Pilots get 25 seats free. Self-serve checkout and invoices are not built (E-006) |

Plan contents and prices are data, validated at startup (the free plan has no paid features; every feature is described and used). Admin editing comes with the admin portal (Phase 17).

## How it works (ADR-021)

- **Entitlements** (`app/billing/entitlements.py`) is the only thing features ask: `require(db, user, "report_pdf")` returns 403 `premium_required` with `details.feature` and `details.pricing_url`. The coach's daily limit comes from the plan.
- **Enforced today:** report PDFs, programmes longer than 7 days, creating relationship invitations (accepting is free), coaching limits. Reports, share cards, assessments, journal, goals and habits stay free.
- **Web payments: Stripe.** `POST /api/v1/billing/checkout` creates a Checkout Session (subscription mode, `client_reference_id` and metadata carry the user and plan). `POST /api/v1/billing/manage` opens the Stripe customer portal for changing or cancelling. Webhooks at `/api/v1/billing/webhooks/stripe` are verified with the signing secret (HMAC-SHA256, 5-minute tolerance) and applied once per event id.
- **Apple and Google: RevenueCat.** The apps identify purchases with the PersonalityDNA user id. RevenueCat webhooks (`/api/v1/billing/webhooks/revenuecat`, shared secret in the Authorization header) update the subscription; `POST /api/v1/billing/restore` re-reads the subscriber from RevenueCat for "Restore purchases". Store subscriptions are managed in the store.
- **No card data** reaches PersonalityDNA: only provider ids, plan, status and period end are stored.
- **Local and e2e testing:** `PDNA_BILLING_DEV_CHECKOUT=true` grants Premium for 30 days without payment, and "manage" toggles cancel at period end. Refused in staging and production.

## Ethics

Clear prices before payment, cancellation from the account page, Premium kept until the end of the paid period, no fake urgency or countdowns, no pre-checked upsells, and a free tier that stays useful.

## Owner setup checklist (needs Deju)

1. Stripe: create the account, two recurring prices, a customer portal configuration and a webhook endpoint for `checkout.session.completed` and `customer.subscription.*`. Set `PDNA_STRIPE_SECRET_KEY`, `PDNA_STRIPE_WEBHOOK_SECRET`, `PDNA_STRIPE_PRICE_IDS`.
2. Apple Developer Program and Google Play Console; create subscription products; connect them in RevenueCat with an entitlement; set the webhook and `PDNA_REVENUECAT_*`.
3. Decide final prices and tax handling (Stripe Tax or equivalent), and update the terms of service.
4. Turn on `PDNA_BILLING_ENFORCE=true`.
