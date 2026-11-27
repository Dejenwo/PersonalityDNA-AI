"use client";

import type { Plan } from "@pdna/api-client";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { annualSaving, priceLabel } from "@/lib/billing";
import { errorMessage } from "@/lib/errors";
import { useAsync } from "@/lib/use-async";

export default function PricingPage() {
  const { state } = useAuth();
  const signedIn = state.status === "signed-in";
  const data = useAsync(
    () => Promise.all([api.plans(), signedIn ? api.billing() : Promise.resolve(null)]),
    `pricing:${state.status}`,
  );
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (state.status === "loading" || data.status === "loading") return <LoadingState label="Loading plans" />;
  if (data.status === "error")
    return (
      <ErrorState
        title="We couldn't load the plans"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  const [plans, billing] = data.data;
  const monthly = plans.plans.find((p) => p.interval === "month");
  const annual = plans.plans.find((p) => p.interval === "year");
  const saving = annualSaving(monthly, annual);

  async function choose(plan: Plan) {
    setBusy(plan.id);
    setError(null);
    try {
      const { url } = await api.checkout(plan.id);
      window.location.assign(url);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(null);
    }
  }

  function action(plan: Plan) {
    if (billing?.plan_id === plan.id && (billing.enforced || plan.id !== "free"))
      return <p className="font-semibold">Your current plan</p>;
    if (plan.price_cents === 0) return null;
    if (!signedIn)
      return (
        <ButtonLink href="/register" variant="secondary">
          Create an account to subscribe
        </ButtonLink>
      );
    if (!plans.checkout_available) return <p className="text-sm text-ink-muted">Subscriptions open soon.</p>;
    if (billing && billing.plan_id !== "free") return null;
    return (
      <Button onClick={() => choose(plan)} disabled={busy !== null}>
        {busy === plan.id ? "Opening checkout…" : `Choose ${plan.name}`}
      </Button>
    );
  }

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl font-bold">Plans and pricing</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">{plans.free_note}</p>
      </header>
      {billing && !billing.enforced && (
        <p className="rounded-card border border-line bg-muted p-4">
          During the preview, every feature is available to every account. Nothing is charged.
        </p>
      )}
      {error && <FormMessage kind="error">{error}</FormMessage>}
      <ul className="grid gap-4 md:grid-cols-3" aria-label="Plans">
        {plans.plans.map((p) => (
          <li key={p.id}>
            <Card className="flex h-full flex-col gap-4" as="div">
              <div>
                <h2 className="text-xl font-semibold">{p.name}</h2>
                <p className="mt-1 text-2xl font-bold">{priceLabel(p, plans.currency)}</p>
                {p.interval === "year" && saving !== null && (
                  <p className="text-sm text-ink-muted">About {saving}% less than paying monthly for a year.</p>
                )}
              </div>
              <ul className="flex-1 list-disc space-y-1 pl-5">
                {p.highlights.map((h) => (
                  <li key={h}>{h}</li>
                ))}
              </ul>
              <div>{action(p)}</div>
            </Card>
          </li>
        ))}
      </ul>
      <p className="max-w-3xl text-sm text-ink-muted">
        {plans.note} Prices are in US dollars and may include tax where it applies. Payments are handled by Stripe on
        the web, and by the App Store or Google Play in the apps; PersonalityDNA never sees your card details.
      </p>
    </div>
  );
}
