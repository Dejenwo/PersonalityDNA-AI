"use client";

import type { OrgSummary } from "@pdna/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FormMessage } from "@/components/form";
import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { TrackView } from "@/components/growth-tracking";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { ROLE_LABEL } from "@/lib/orgs";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function OrgsPage() {
  const auth = useRequireSignIn();
  const userId = auth.status === "signed-in" ? auth.user.id : "";
  const data = useAsync(() => (userId ? api.orgs() : Promise.resolve(null)), userId);

  if (auth.status !== "signed-in" || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading your organisations" />;
  if (data.status === "error")
    return (
      <ErrorState
        title="We couldn't load your organisations"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  const { organisations, policy_version } = data.data!;
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <TrackView event="organisations_view" />
      <header>
        <h1 className="text-3xl font-bold">Organisations</h1>
        <p className="mt-2 text-ink-muted">
          Teams, schools and coaching groups can run voluntary development programmes here. An organisation sees who its
          members are, never their answers, results, reports, journal or coaching.
        </p>
      </header>

      <section aria-labelledby="mine-heading">
        <h2 id="mine-heading" className="text-xl font-semibold">
          Your organisations
        </h2>
        {organisations.length === 0 ? (
          <EmptyState
            title="You're not in any organisation"
            message="If someone sends you a join link, open it to see what joining means. You can also start one below."
          />
        ) : (
          <ul className="mt-4 space-y-3">
            {organisations.map((o: OrgSummary) => (
              <li key={o.id}>
                <Link
                  href={`/orgs/${o.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line bg-surface p-4 hover:bg-muted"
                >
                  <span>
                    <span className="block font-semibold">{o.name}</span>
                    <span className="text-sm text-ink-muted">{ROLE_LABEL[o.role]}</span>
                  </span>
                  <span className="text-sm text-primary">Open</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      <CreateOrg policyVersion={policy_version} />
    </div>
  );
}

function CreateOrg({ policyVersion }: { policyVersion: string }) {
  const router = useRouter();
  const [name, setName] = useState("");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (!agreed) {
      setError("Please confirm how organisations work.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const org = await api.createOrg(name, policyVersion);
      router.push(`/orgs/${org.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="create-heading">
      <h2 id="create-heading" className="text-xl font-semibold">
        Start an organisation
      </h2>
      <p className="mt-2 text-sm text-ink-muted">
        New organisations start as a free pilot with a limited number of seats. For a larger licence, which also gives
        members Premium features, contact us.
      </p>
      <form onSubmit={create} className="mt-4 space-y-4">
        <div>
          <label htmlFor="org-name" className="font-medium">
            Name
          </label>
          <input
            id="org-name"
            required
            minLength={2}
            maxLength={120}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
          />
        </div>
        <label className="flex gap-3">
          <input
            type="checkbox"
            className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
          />
          <span>
            I understand that taking part is voluntary for everyone, that I will see members&apos; names and emails but
            never their results, and that PersonalityDNA must not be used for hiring, promotion, pay or other employment
            decisions.
          </span>
        </label>
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create organisation"}
        </Button>
      </form>
    </Card>
  );
}
