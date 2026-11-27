"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { kindsLabel } from "@/lib/reports";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

const when = (iso: string) => new Date(iso).toLocaleString(undefined, { dateStyle: "long", timeStyle: "short" });

export default function ReportsPage() {
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const list = useAsync(() => (signedIn ? api.reports() : Promise.resolve(null)), `reports:${signedIn}`);
  const router = useRouter();
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    setCreating(true);
    setError(null);
    try {
      const r = await api.createReport();
      router.push(`/reports/${r.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setCreating(false);
    }
  }

  if (!signedIn || list.status === "loading" || (list.status === "success" && !list.data))
    return <LoadingState label="Loading your reports" />;
  if (list.status === "error")
    return (
      <ErrorState
        title="We couldn't load your reports"
        message={errorMessage(list.error)}
        action={<Button onClick={list.reload}>Try again</Button>}
      />
    );
  const reports = list.data!.reports;

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">Personality reports</h1>
          <p className="mt-2 max-w-2xl text-ink-muted">
            A report brings together your latest Big Five, career interest and leadership results, with a suggested
            development plan. Each report is a snapshot: it doesn&apos;t change if you take an assessment again.
          </p>
        </div>
        <Button onClick={create} disabled={creating}>
          {creating ? "Creating…" : "Create a new report"}
        </Button>
      </header>
      {error && <FormMessage kind="error">{error}</FormMessage>}

      {reports.length === 0 ? (
        <EmptyState
          title="No reports yet"
          message="Take the Big Five assessment while signed in, then create your first report."
          action={<ButtonLink href="/discover" variant="secondary">Find an assessment</ButtonLink>}
        />
      ) : (
        <ul className="space-y-3" aria-label="Your reports">
          {reports.map((r) => (
            <li key={r.id}>
              <Card className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">
                    <Link href={`/reports/${r.id}`} className="underline-offset-4 hover:underline">
                      {r.headline}
                    </Link>
                  </p>
                  <p className="text-sm text-ink-muted">
                    {when(r.created_at)} · {kindsLabel(r.kinds)}
                  </p>
                </div>
                <ButtonLink href={`/reports/${r.id}`} variant="secondary">
                  Open report
                </ButtonLink>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
