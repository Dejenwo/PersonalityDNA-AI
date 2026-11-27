"use client";

import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { subscriptionSummary } from "@/lib/billing";
import { errorMessage } from "@/lib/errors";
import { useAsync } from "@/lib/use-async";

/** Plan, renewal and a way to change or cancel, on the account page. */
export function BillingCard() {
  const data = useAsync(() => api.billing(), "billing");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function manage() {
    setBusy(true);
    setError(null);
    try {
      const { url } = await api.manageSubscription();
      if (url.startsWith(window.location.origin)) {
        data.reload();
        setBusy(false);
      } else {
        window.location.assign(url);
      }
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="plan-heading">
      <h2 id="plan-heading" className="text-xl font-semibold">
        Your plan
      </h2>
      {data.status === "loading" ? (
        <LoadingState label="Loading your plan" />
      ) : data.status === "error" ? (
        <ErrorState
          title="We couldn't load your plan"
          message={errorMessage(data.error)}
          action={<Button onClick={data.reload}>Try again</Button>}
        />
      ) : (
        <>
          <p className="mt-1">{subscriptionSummary(data.data)}</p>
          <p className="mt-1 text-sm text-ink-muted">
            AI coaching: up to {data.data.coach_daily_messages} messages a day.
          </p>
          {data.data.subscription?.provider === "revenuecat" && data.data.plan_id !== "free" && (
            <p className="mt-1 text-sm text-ink-muted">
              You subscribed in the app. Change or cancel it in the App Store or Google Play.
            </p>
          )}
          <div className="mt-4 flex flex-wrap gap-3">
            {data.data.manage_available ? (
              <Button variant="secondary" onClick={manage} disabled={busy}>
                {data.data.subscription?.cancel_at_period_end ? "Resume or change subscription" : "Manage or cancel subscription"}
              </Button>
            ) : (
              <ButtonLink href="/pricing" variant="secondary">
                See plans
              </ButtonLink>
            )}
          </div>
          {error && <FormMessage kind="error">{error}</FormMessage>}
        </>
      )}
    </Card>
  );
}
