"use client";

import type { JournalEntry, JournalPrompts } from "@pdna/api-client";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { JournalForm } from "@/components/journal-form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { formatEntryDate } from "@/lib/journal";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function JournalEntryPage() {
  const { entryId } = useParams<{ entryId: string }>();
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(
    () =>
      signedIn
        ? Promise.all([api.journalEntry(entryId), api.journalPrompts()])
        : Promise.resolve(null),
    `${entryId}:${signedIn}`,
  );

  if (!signedIn || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the entry" />;
  if (data.status === "error")
    return (
      <ErrorState
        title={isNotFound(data.error) ? "Entry not found" : "We couldn't load this entry"}
        message={isNotFound(data.error) ? "It may have been deleted." : errorMessage(data.error)}
        action={<ButtonLink href="/journal">Back to the journal</ButtonLink>}
      />
    );
  const [entry, prompts] = data.data!;
  return <Entry key={entry.id} initial={entry} prompts={prompts} />;
}

function Entry({ initial, prompts }: { initial: JournalEntry; prompts: JournalPrompts }) {
  const router = useRouter();
  const [entry, setEntry] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const kind = prompts.kinds.find((k) => k.id === entry.kind);

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteJournalEntry(entry.id);
      router.push("/journal");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <ButtonLink href="/journal" variant="ghost" className="-ml-5">
          ← Journal
        </ButtonLink>
        <p className="text-sm text-ink-muted">
          {formatEntryDate(entry.entry_date)} · {kind?.label ?? entry.kind}
        </p>
        <h1 className="text-3xl font-bold">{editing ? "Edit entry" : (entry.title ?? kind?.label ?? "Entry")}</h1>
      </header>

      {editing ? (
        <JournalForm
          prompts={prompts}
          initial={entry}
          submitLabel="Save changes"
          onSubmit={async (body) => {
            setEntry(await api.updateJournalEntry(entry.id, body));
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <>
          <Card as="article">
            <p className="whitespace-pre-wrap">{entry.body}</p>
            {(entry.mood || entry.tags.length > 0) && (
              <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-1 text-sm text-ink-muted">
                {entry.mood && (
                  <div className="flex gap-1">
                    <dt>Mood:</dt>
                    <dd>{prompts.mood_scale[entry.mood - 1]}</dd>
                  </div>
                )}
                {entry.tags.length > 0 && (
                  <div className="flex gap-1">
                    <dt>Tags:</dt>
                    <dd>{entry.tags.join(", ")}</dd>
                  </div>
                )}
              </dl>
            )}
          </Card>
          {confirming ? (
            <div className="rounded-card border border-line p-4" role="group" aria-label="Confirm deletion">
              <p>Delete this entry? This can&apos;t be undone.</p>
              <div className="mt-3 flex flex-wrap gap-3">
                <Button onClick={remove} disabled={busy}>
                  Yes, delete it
                </Button>
                <Button variant="secondary" onClick={() => setConfirming(false)} disabled={busy}>
                  Cancel
                </Button>
              </div>
            </div>
          ) : (
            <div className="flex flex-wrap gap-3">
              <Button onClick={() => setEditing(true)}>Edit</Button>
              <Button variant="secondary" onClick={() => setConfirming(true)}>
                Delete
              </Button>
            </div>
          )}
          {error && <FormMessage kind="error">{error}</FormMessage>}
        </>
      )}
    </div>
  );
}
