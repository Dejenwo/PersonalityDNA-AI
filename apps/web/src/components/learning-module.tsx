"use client";

import type { LearningModule, LearningTrack, ModuleList } from "@pdna/api-client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage, isNotFound } from "@/lib/errors";
import { modulePath, TRACKS } from "@/lib/learning";
import { useAsync } from "@/lib/use-async";

/** A learning module page (lessons, activities with progress, reflection) for any learning track. */
export function LearningModulePage({ track }: { track: LearningTrack }) {
  const { moduleId } = useParams<{ moduleId: string }>();
  const { state: auth } = useAuth();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(
    () => (auth.status === "loading" ? Promise.resolve(null) : api.learningModule(track, moduleId)),
    `${track}:${moduleId}:${auth.status}`,
  );

  if (data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the module" />;
  if (data.status === "error")
    return (
      <ErrorState
        title={isNotFound(data.error) ? "Module not found" : "We couldn't load this module"}
        message={isNotFound(data.error) ? "It may have been renamed." : errorMessage(data.error)}
        action={<ButtonLink href={TRACKS[track].path}>All modules</ButtonLink>}
      />
    );
  return <Module track={track} m={data.data!} signedIn={signedIn} />;
}

function Module({ track, m, signedIn }: { track: LearningTrack; m: LearningModule; signedIn: boolean }) {
  const t = TRACKS[track];
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <ButtonLink href={t.path} variant="ghost" className="-ms-5">
          ← {m.track_title}
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
            <Link href={`/login?next=${encodeURIComponent(modulePath(track, m.id))}`} className="text-primary underline">
              Sign in
            </Link>{" "}
            to mark activities as done.
          </p>
        )}
        {m.activities.map((a) => (
          <ActivityCard key={a.id} track={track} moduleId={m.id} a={a} signedIn={signedIn} />
        ))}
      </section>

      <Card>
        <h2 className="text-lg font-semibold">Reflect</h2>
        <p className="mt-1">{m.reflection}</p>
        <ButtonLink href={`/coach?topic=${t.coachTopic}`} variant="secondary" className="mt-4">
          Reflect with the coach
        </ButtonLink>
      </Card>
      {m.support_note && <SupportNote text={m.support_note} />}
    </div>
  );
}

function ActivityCard({
  track,
  moduleId,
  a,
  signedIn,
}: {
  track: LearningTrack;
  moduleId: string;
  a: LearningModule["activities"][number];
  signedIn: boolean;
}) {
  const [done, setDone] = useState(a.completed_at !== null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle() {
    setBusy(true);
    setError(null);
    try {
      await api.setActivityDone(track, moduleId, a.id, !done);
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
      <ol className="mt-2 list-decimal space-y-1 ps-5 text-ink-muted">
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

/** Where to find help. Shown on tracks that touch on feelings and stress. */
export function SupportNote({ text }: { text: string }) {
  return (
    <aside aria-label="Getting support" className="rounded-card border border-line bg-muted p-4 text-sm">
      <p className="font-semibold">Need more support?</p>
      <p className="mt-1">{text}</p>
    </aside>
  );
}

/** Every module of a track as a grid of links, with activity progress for signed-in users. */
export function ModuleGrid({ track, list, signedIn }: { track: LearningTrack; list: ModuleList; signedIn: boolean }) {
  return (
    <section aria-labelledby="all-heading">
      <h2 id="all-heading" className="text-2xl font-bold">
        All modules
      </h2>
      {!signedIn && (
        <p className="mt-1 text-sm text-ink-muted">
          <Link href={`/login?next=${encodeURIComponent(TRACKS[track].path)}`} className="text-primary underline">
            Sign in
          </Link>{" "}
          to keep track of the activities you finish.
        </p>
      )}
      <ul className="mt-4 grid gap-4 sm:grid-cols-2">
        {list.modules.map((m) => (
          <li key={m.id}>
            <Link
              href={modulePath(track, m.id)}
              className="block h-full rounded-card border border-line bg-surface p-5 hover:bg-muted"
            >
              <span className="block text-lg font-semibold">{m.title}</span>
              <span className="mt-1 block text-sm text-ink-muted">{m.summary}</span>
              {signedIn && (
                <span className="mt-2 block text-sm">
                  {m.activities_done} of {m.activities_total} activities done
                </span>
              )}
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
