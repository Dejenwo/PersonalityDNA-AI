"use client";

import { ModuleGrid, SupportNote } from "@/components/learning-module";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";
import { useAsync } from "@/lib/use-async";

export default function EmotionalAwarenessPage() {
  const { state: auth } = useAuth();
  const signedIn = auth.status === "signed-in";
  const modules = useAsync(
    () => (auth.status === "loading" ? Promise.resolve(null) : api.learningModules("emotional-awareness")),
    `modules:${auth.status}`,
  );

  if (modules.status === "loading" || (modules.status === "success" && !modules.data))
    return <LoadingState label="Loading emotional awareness" />;
  if (modules.status === "error")
    return (
      <ErrorState level={1}
        title="We couldn't load emotional awareness"
        message={errorMessage(modules.error)}
        action={<Button onClick={modules.reload}>Try again</Button>}
      />
    );
  const list = modules.data!;

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl font-bold">{list.title}</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Short modules on noticing your feelings, pausing before you respond, listening, seeing other points of view
          and saying what you need. Each has two ideas to read, two small activities to try and a question to reflect
          on. {list.note}
        </p>
      </header>

      <Card as="section" aria-labelledby="start-heading">
        <h2 id="start-heading" className="text-xl font-semibold">
          Where to start
        </h2>
        <p className="mt-2 text-ink-muted">
          There is no test here and no right order. Pick the module that matches something you would like to handle
          differently this week, try one activity, and come back to the reflection question when you have.
        </p>
      </Card>

      <ModuleGrid track="emotional-awareness" list={list} signedIn={signedIn} />

      <Card>
        <h2 className="text-lg font-semibold">Talk it through</h2>
        <p className="mt-1 text-ink-muted">
          The coach can help you prepare a difficult conversation or put a feeling into words.
        </p>
        <ButtonLink href="/coach?topic=emotions" variant="secondary" className="mt-4">
          Open the coach
        </ButtonLink>
      </Card>

      {list.support_note && <SupportNote text={list.support_note} />}
    </div>
  );
}
