"use client";

import type { JournalKind } from "@pdna/api-client";
import { useRouter } from "next/navigation";
import { JournalForm } from "@/components/journal-form";
import { Button, ButtonLink, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function NewJournalEntryPage() {
  const auth = useRequireSignIn();
  const router = useRouter();
  const prompts = useAsync(() => api.journalPrompts(), "journal-prompts");

  if (auth.status !== "signed-in" || prompts.status === "loading") return <LoadingState label="Loading" />;
  if (prompts.status === "error")
    return (
      <ErrorState
        title="We couldn't load the journal"
        message={errorMessage(prompts.error)}
        action={<Button onClick={prompts.reload}>Try again</Button>}
      />
    );
  const asked = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("kind");
  const kind = prompts.data.kinds.find((k) => k.id === asked)?.id as JournalKind | undefined;

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <header>
        <ButtonLink href="/journal" variant="ghost" className="-ml-5">
          ← Journal
        </ButtonLink>
        <h1 className="text-3xl font-bold">New entry</h1>
      </header>
      <JournalForm
        prompts={prompts.data}
        initialKind={kind}
        submitLabel="Save entry"
        onSubmit={async (body) => {
          const e = await api.createJournalEntry(body);
          router.push(`/journal/${e.id}`);
        }}
        onCancel={() => router.push("/journal")}
      />
    </div>
  );
}
