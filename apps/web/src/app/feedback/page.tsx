"use client";

import type { Feedback, FeedbackIn } from "@pdna/api-client";
import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { FormMessage } from "@/components/form";
import { Button, Card, LoadingState } from "@/components/ui";
import { useI18n } from "@/i18n/provider";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

const KINDS: { value: FeedbackIn["kind"]; label: string }[] = [
  { value: "bug", label: "Something isn't working" },
  { value: "idea", label: "An idea or request" },
  { value: "content", label: "Wording or content" },
  { value: "accessibility", label: "Accessibility" },
  { value: "other", label: "Something else" },
];
const STATUS: Record<Feedback["status"], string> = {
  new: "Received",
  planned: "Planned",
  fixed: "Fixed",
  closed: "Closed",
};
const MAX = 2000;

export default function FeedbackPage() {
  return (
    <Suspense fallback={<LoadingState label="Loading" />}>
      <FeedbackForm />
    </Suspense>
  );
}

function FeedbackForm() {
  const auth = useAuth();
  const signedIn = auth.state.status === "signed-in";
  // The screen the person came from, path only (no query string, which can hold tokens).
  const from = useSearchParams().get("from");
  const page = from && from.startsWith("/") && !from.startsWith("//") ? from.split(/[?#]/)[0] : undefined;
  const [kind, setKind] = useState<FeedbackIn["kind"]>("bug");
  const [message, setMessage] = useState("");
  const [contact, setContact] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);
  const [mine, setMine] = useState<Feedback[] | null>(null);

  useEffect(() => {
    if (!signedIn) return;
    api.myFeedback().then((r) => setMine(r.items), () => setMine(null));
  }, [signedIn, sent]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (message.trim().length < 10) {
      setError("Please write at least 10 characters so we can understand it.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api.sendFeedback({
        kind,
        message,
        page,
        app_version: process.env.NEXT_PUBLIC_APP_VERSION ?? "web",
        contact_ok: signedIn && contact,
      });
      setSent(true);
      setMessage("");
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <header>
        <h1 className="text-3xl font-bold">Send feedback</h1>
        <p className="mt-2 text-ink-muted">
          Tell us what isn&apos;t working, what&apos;s confusing or what you&apos;d like. A small team reads every
          message. Please don&apos;t include passwords, health details or other people&apos;s personal information.
        </p>
      </header>

      {sent ? (
        <Card>
          <FormMessage kind="success">Thank you. We&apos;ve received your feedback.</FormMessage>
          <Button variant="secondary" className="mt-4" onClick={() => setSent(false)}>
            Send something else
          </Button>
        </Card>
      ) : (
        <form onSubmit={submit} className="space-y-6" noValidate>
          <fieldset>
            <legend className="font-medium">What is it about?</legend>
            <div className="mt-2 grid gap-2 sm:grid-cols-2">
              {KINDS.map((k) => (
                <label key={k.value} className="flex min-h-12 items-center gap-3 rounded-xl border border-line px-4 py-2">
                  <input
                    type="radio"
                    className="h-5 w-5 accent-[var(--pdna-primary)]"
                    name="kind"
                    value={k.value}
                    checked={kind === k.value}
                    onChange={() => setKind(k.value)}
                  />
                  {k.label}
                </label>
              ))}
            </div>
          </fieldset>
          <div>
            <label htmlFor="feedback-message" className="block font-medium">
              Your message
            </label>
            <textarea
              id="feedback-message"
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              maxLength={MAX}
              rows={7}
              required
              aria-describedby="feedback-message-hint"
              className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
            />
            <p id="feedback-message-hint" className="mt-1 text-sm text-ink-muted">
              For a problem, say what you did, what you expected and what happened instead.
              {page && ` We'll note that you came from ${page}.`}
              {message.length > MAX - 300 && ` ${MAX - message.length} characters left.`}
            </p>
          </div>
          {signedIn ? (
            <label className="flex items-start gap-3">
              <input
                type="checkbox"
                className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
                checked={contact}
                onChange={(e) => setContact(e.target.checked)}
              />
              <span>
                You may contact me about this by email.{" "}
                <span className="text-ink-muted">Otherwise our support team doesn&apos;t see which account sent it.</span>
              </span>
            </label>
          ) : (
            <p className="text-sm text-ink-muted">
              You&apos;re not signed in, so this is sent anonymously and we can&apos;t reply.
            </p>
          )}
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <Button type="submit" disabled={busy}>
            {busy ? "Sending…" : "Send feedback"}
          </Button>
        </form>
      )}

      {signedIn && mine && mine.length > 0 && <Sent items={mine} />}
    </div>
  );
}

function Sent({ items }: { items: Feedback[] }) {
  const { formatDate } = useI18n();
  return (
    <section aria-labelledby="sent-heading">
      <h2 id="sent-heading" className="text-xl font-semibold">
        What you&apos;ve sent
      </h2>
      <ul className="mt-3 space-y-3">
        {items.map((f) => (
          <li key={f.id} className="rounded-card border border-line p-4">
            <p className="text-sm text-ink-muted">
              {formatDate(f.created_at)} · {KINDS.find((k) => k.value === f.kind)?.label} ·{" "}
              <strong className="text-ink">{STATUS[f.status]}</strong>
            </p>
            <p className="mt-1 whitespace-pre-wrap break-words">{f.message}</p>
          </li>
        ))}
      </ul>
    </section>
  );
}
