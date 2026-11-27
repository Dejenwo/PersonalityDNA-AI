import type { Billing } from "@pdna/api-client";
import { describe, expect, it } from "vitest";
import { annualSaving, priceLabel, subscriptionSummary } from "./billing";

const plan = (price_cents: number, interval: "month" | "year" | null) =>
  ({ id: "x", name: "x", price_cents, interval, features: [], coach_daily_messages: 5, highlights: [] }) as never;

const billing = (over: Partial<Billing>): Billing => ({
  enforced: true,
  plan_id: "premium-monthly",
  plan_name: "Premium monthly",
  features: [],
  coach_daily_messages: 30,
  subscription: {
    provider: "stripe",
    plan_id: "premium-monthly",
    status: "active",
    current_period_end: "2026-12-27T12:00:00Z",
    cancel_at_period_end: false,
  },
  manage_available: true,
  ...over,
});

describe("billing", () => {
  it("formats prices", () => {
    expect(priceLabel(plan(999, "month"))).toBe("$9.99 a month");
    expect(priceLabel(plan(6999, "year"))).toBe("$69.99 a year");
    expect(priceLabel(plan(0, null))).toBe("Free");
  });

  it("works out the annual saving honestly", () => {
    expect(annualSaving(plan(999, "month"), plan(6999, "year"))).toBe(41);
    expect(annualSaving(plan(999, "month"), plan(12000, "year"))).toBeNull();
  });

  it("describes the subscription", () => {
    expect(subscriptionSummary(billing({ enforced: false, plan_id: "free", subscription: null }))).toMatch(
      /every feature is available/,
    );
    expect(subscriptionSummary(billing({ plan_id: "free", subscription: null }))).toBe("You're on the free plan.");
    expect(subscriptionSummary(billing({}), "en-GB")).toBe("Premium monthly, renews on 27 December 2026.");
    const ending = billing({});
    ending.subscription!.cancel_at_period_end = true;
    expect(subscriptionSummary(ending, "en-GB")).toBe("Premium monthly ends on 27 December 2026. It won't renew.");
  });
});
