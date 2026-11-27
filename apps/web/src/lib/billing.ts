import type { Billing, Plan } from "@pdna/api-client";

/** "$9.99 a month", "$69.99 a year" or "Free". Prices come from the server's plan list. */
export function priceLabel(plan: Pick<Plan, "price_cents" | "interval">, currency = "USD", locale = "en-US"): string {
  if (plan.price_cents === 0) return "Free";
  const amount = new Intl.NumberFormat(locale, { style: "currency", currency }).format(plan.price_cents / 100);
  return plan.interval ? `${amount} a ${plan.interval}` : amount;
}

/** What the annual plan saves over twelve monthly payments, as a whole percentage, or null. */
export function annualSaving(monthly?: Plan, annual?: Plan): number | null {
  if (!monthly || !annual || monthly.price_cents <= 0) return null;
  const saving = 1 - annual.price_cents / (monthly.price_cents * 12);
  return saving > 0 ? Math.floor(saving * 100) : null;
}

/** One plain sentence about the subscription's state for the account page. */
export function subscriptionSummary(b: Billing, locale?: string): string {
  const s = b.subscription;
  if (!s || b.plan_id === "free")
    return b.enforced ? "You're on the free plan." : "During the preview, every feature is available to every account.";
  const end = s.current_period_end
    ? new Date(s.current_period_end).toLocaleDateString(locale, { dateStyle: "long" })
    : null;
  if (s.cancel_at_period_end) return end ? `${b.plan_name} ends on ${end}. It won't renew.` : `${b.plan_name} won't renew.`;
  if (s.status === "past_due") return `There's a problem with your last payment for ${b.plan_name}. Please update your payment details.`;
  return end ? `${b.plan_name}, renews on ${end}.` : `${b.plan_name} is active.`;
}
