"use client";

import type { CoachStatus, ConversationSummary } from "@pdna/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { COACH_TOPICS } from "@/lib/coach";
import { errorMessage } from "@/lib/errors";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function CoachPage() {
  const auth = useRequireSignIn();
  const userId = auth.status === "signed-in" ? auth.user.id : "";
  const data = useAsync(
    async () => {
      if (!userId) return null;
      const status = await api.coachStatus();
      const list = status.enabled && status.email_verified ? (await api.listConversations()).items : [];
      return { status, list };
    },
    userId,
  );

  if (auth.status !== "signed-in" || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the coach" />;
  if (data.status === "error")
    return (
      <ErrorState
        title="We couldn't load the coach"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  const { status, list } = data.data!;
  if (!status.enabled)
    return <ErrorState title="The coach is unavailable" message="The coach is switched off right now. Please try again later." />;
  if (!status.email_verified)
    return (
      <ErrorState
        title="Verify your email to use the coach"
        message="We sent a link to your email address when you signed up. Open it, then come back here."
      />
    );

  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <header>
        <h1 className="text-3xl font-bold">PersonalityDNA Coach</h1>
        <p className="mt-2 text-ink-muted">
          Talk through your results and everyday situations with an AI coach. It explains and suggests; it doesn&apos;t
          diagnose, and it isn&apos;t a therapist.
        </p>
        <p className="mt-2 text-sm text-ink-muted">
          {status.remaining} of {status.daily_limit} messages left in the last 24 hours.
        </p>
      </header>

      {status.demo_mode && (
        <Card role="note" className="border-accent">
          <h2 className="font-semibold">Demo mode</h2>
          <p className="mt-1 text-ink-muted">
            Replies currently come from a built-in stand-in that only repeats facts from your results. No AI service is
            used and nothing leaves PersonalityDNA.
          </p>
        </Card>
      )}

      <StartConversation status={status} />

      <section aria-labelledby="conversations-heading">
        <h2 id="conversations-heading" className="text-xl font-semibold">
          Your conversations
        </h2>
        {list.length === 0 ? (
          <EmptyState title="No conversations yet" message="Start one above. You can delete conversations at any time." />
        ) : (
          <ul className="mt-4 space-y-3">
            {list.map((c) => (
              <ConversationRow key={c.id} c={c} />
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function ConversationRow({ c }: { c: ConversationSummary }) {
  const updated = new Date(c.updated_at).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
  return (
    <li>
      <Link
        href={`/coach/${c.id}`}
        className="flex items-center justify-between gap-4 rounded-card border border-line bg-surface p-4 hover:bg-muted"
      >
        <span>
          <span className="block font-semibold">{c.title}</span>
          <span className="text-sm text-ink-muted">
            {c.message_count} message{c.message_count === 1 ? "" : "s"} · {c.uses_results ? "uses your results" : "no results shared"}
          </span>
        </span>
        <span className="text-sm text-ink-muted">{updated}</span>
      </Link>
    </li>
  );
}

function StartConversation({ status }: { status: CoachStatus }) {
  const router = useRouter();
  const [topic, setTopic] = useState(COACH_TOPICS[0]!.id);
  const [useResults, setUseResults] = useState(true);
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start(e: FormEvent) {
    e.preventDefault();
    if (!agreed) {
      setError("Please confirm you understand how the coach works.");
      return;
    }
    setBusy(true);
    setError(null);
    const resultId = new URLSearchParams(window.location.search).get("result");
    try {
      const conv = await api.createConversation({
        consent: { accepted: true, policy_version: status.consent_policy_version },
        topic,
        use_results: status.has_results && useResults,
        result_id: status.has_results && useResults && resultId ? resultId : null,
      });
      router.push(`/coach/${conv.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="start-heading">
      <h2 id="start-heading" className="text-xl font-semibold">
        Start a conversation
      </h2>
      <form onSubmit={start} className="mt-4 space-y-6">
        <fieldset>
          <legend className="font-medium">What would you like to talk about?</legend>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {COACH_TOPICS.map((t) => (
              <label
                key={t.id}
                className="flex cursor-pointer gap-3 rounded-card border border-line p-3 has-[:checked]:border-primary has-[:checked]:bg-muted"
              >
                <input
                  type="radio"
                  name="topic"
                  value={t.id}
                  checked={topic === t.id}
                  onChange={() => setTopic(t.id)}
                  className="mt-1"
                />
                <span>
                  <span className="block font-medium">{t.label}</span>
                  <span className="text-sm text-ink-muted">{t.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        {status.has_results ? (
          <label className="flex gap-3">
            <input
              type="checkbox"
              checked={useResults}
              onChange={(e) => setUseResults(e.target.checked)}
              className="mt-1"
            />
            <span>
              Let the coach use my latest results
              <span className="block text-sm text-ink-muted">
                Your trait scores, bands and archetype. Never your individual answers.
              </span>
            </span>
          </label>
        ) : (
          <p className="text-ink-muted">
            You haven&apos;t completed an assessment on this account yet, so the coach won&apos;t know your results.{" "}
            <Link href="/discover" className="underline">
              Take an assessment
            </Link>{" "}
            for more personal coaching.
          </p>
        )}

        <div className="rounded-card bg-muted p-4 text-sm">
          <h3 className="font-semibold">Before you start</h3>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-ink-muted">
            <li>
              {status.demo_mode
                ? "In demo mode nothing is sent to an AI service."
                : "Your messages, and your scores if you allow it, are sent to our AI provider to write replies."}{" "}
              Your name, email address and individual answers are never sent.
            </li>
            <li>Conversations are stored encrypted. You can delete them, or your whole account, at any time.</li>
            <li>The coach is an AI. It can be wrong, it isn&apos;t a therapist and it can&apos;t diagnose anything.</li>
            <li>If you are in danger or crisis, contact local emergency services or a crisis line.</li>
          </ul>
          <label className="mt-3 flex gap-3 font-medium">
            <input type="checkbox" checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-1" />
            I understand and want to use the coach
          </label>
        </div>

        {error && <FormMessage kind="error">{error}</FormMessage>}
        <div className="flex flex-wrap items-center gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Starting…" : "Start conversation"}
          </Button>
          <ButtonLink href="/privacy" variant="ghost">
            Privacy notice
          </ButtonLink>
        </div>
      </form>
    </Card>
  );
}
