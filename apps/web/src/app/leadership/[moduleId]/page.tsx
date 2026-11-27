"use client";

import type { LeadershipModule } from "@pdna/api-client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage, isNotFound } from "@/lib/errors";
import { useAsync } from "@/lib/use-async";

export default function ModulePage() {
  const { moduleId } = useParams<{ moduleId: string }>();
  const { state: auth } = useAuth();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(
    () => (auth.status === "loading" ? Promise.resolve(null) : api.leadershipModule(moduleId)),
    `${moduleId}:${auth.status}`,
  );

  if (data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the module" />;
  if (data.status === "error")
    return (
      <ErrorState
        title={isNotFound(data.error) ? "Module not found" : "We couldn't load this module"}
        message={isNotFound(data.error) ? "It may have been renamed." : errorMessage(data.error)}
        action={<ButtonLink href="/leadership">All modules</ButtonLink>}
      />
    );
  return <Module m={data.data!} signedIn={signedIn} />;
}

function Module({ m, signedIn }: { m: LeadershipModule; signedIn: boolean }) {
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <ButtonLink href="/leadership" variant="ghost" className="-ml-5">
          ← Leadership
        </ButtonLink>
        <h1 className="text-3xl font-bold">{m.title}</h1>
        <p className="mt-2 text-ink-muted">{m.summary}</p>
      </header>

      <section aria-labelledby="learn-heading" className="space-y-4">
        <h2 id="learn-heading" className="text-2xl font-bold">
          Learn
        </h2>
        {m.lessons.map((l) => (
          <Card key={l.title} as="article">
            <h3 className="font-semibold">{l.title}</h3>
            <p className="mt-1 text-ink-muted">{l.text}</p>
          </Card>
        ))}
      </section>

      <section aria-labelledby="practise-heading" className="space-y-4">
        <h2 id="practise-heading" className="text-2xl font-bold">
          Practise
        </h2>
        {!signedIn && (
          <p className="text-sm text-ink-muted">
            <Link href={`/login?next=${encodeURIComponent(`/leadership/${m.id}`)}`} className="text-primary underline">
              Sign in
            </Link>{" "}
            to mark activities as done.
          </p>
        )}
        {m.activities.map((a) => (
          <ActivityCard key={a.id} moduleId={m.id} a={a} signedIn={signedIn} />
        ))}
      </section>

      <Card>
        <h2 className="text-lg font-semibold">Reflect</h2>
        <p className="mt-1">{m.reflection}</p>
        <ButtonLink href="/coach?topic=leadership" variant="secondary" className="mt-4">
          Reflect with the coach
        </ButtonLink>
      </Card>
    </div>
  );
}

function ActivityCard({
  moduleId,
  a,
  signedIn,
}: {
  moduleId: string;
  a: LeadershipModule["activities"][number];
  signedIn: boolean;
}) {
  const [done, setDone] = useState(a.completed_at !== null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      await api.setActivityDone(moduleId, a.id, !done);
      setDone(!done);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="article">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">{a.title}</h3>
        {done && <span className="rounded-full border border-line px-2 py-0.5 text-xs">Done</span>}
      </div>
      <ol className="mt-2 list-decimal space-y-1 pl-5 text-ink-muted">
        {a.steps.map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
      {signedIn && (
        <Button variant="secondary" className="mt-4" onClick={toggle} disabled={busy}>
          {done ? `Mark "${a.title}" as not done` : `Mark "${a.title}" as done`}
        </Button>
      )}
      {error && <FormMessage kind="error">{error}</FormMessage>}
    </Card>
  );
}
