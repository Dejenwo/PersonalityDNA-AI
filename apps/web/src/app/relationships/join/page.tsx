"use client";

import type { InvitationPreview } from "@pdna/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { captureInviteToken, forgetInviteToken, otherName, relationLabel } from "@/lib/relationships";
import { useRequireSignIn } from "@/lib/require-auth";

function sessionStore() {
  try {
    return window.sessionStorage;
  } catch {
    return null;
  }
}

type Load =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error"; error: unknown }
  | { status: "ready"; token: string; preview: InvitationPreview };

export default function JoinPage() {
  // Capture the token before the sign-in redirect can drop the fragment.
  const token = useRef<string | null>(null);
  useEffect(() => {
    token.current = captureInviteToken(window.location, sessionStore());
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
  }, []);
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const [load, setLoad] = useState<Load>({ status: "loading" });

  useEffect(() => {
    if (!signedIn) return;
    const t = token.current;
    let alive = true;
    const next: Promise<Load> = t
      ? api.previewInvitation(t).then(
          (preview): Load => ({ status: "ready", token: t, preview }),
          (error: unknown): Load => {
            if (isNotFound(error)) forgetInviteToken(sessionStore());
            return { status: "error", error };
          },
        )
      : Promise.resolve({ status: "missing" });
    void next.then((l) => alive && setLoad(l));
    return () => {
      alive = false;
    };
  }, [signedIn]);

  if (load.status === "loading") return <LoadingState label="Loading the invitation" />;
  if (load.status === "missing" || load.status === "error") {
    const gone = load.status === "missing" || isNotFound(load.error);
    return (
      <ErrorState
        title={gone ? "This invitation isn't available" : "We couldn't load this invitation"}
        message={
          gone
            ? "The link may be incomplete, already used, cancelled or expired. Ask for a new one."
            : errorMessage(load.error)
        }
        action={<ButtonLink href="/relationships">Relationships</ButtonLink>}
      />
    );
  }
  return <Accept token={load.token} preview={load.preview} />;
}

function Accept({ token, preview }: { token: string; preview: InvitationPreview }) {
  const router = useRouter();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const who = preview.inviter_name?.trim() || "Someone";

  async function accept(e: FormEvent) {
    e.preventDefault();
    if (!agreed) {
      setError("Please confirm what will be shared.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const link = await api.acceptInvitation(token, preview.policy_version);
      forgetInviteToken(sessionStore());
      router.push(`/relationships/${link.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">
        {who} invited you to compare results
      </h1>
      <Card>
        <p>
          They invited you as their {relationLabel(preview.relation_type).toLowerCase()}. If you accept, you each see
          whether the other&apos;s Big Five traits are lower, middle or higher, with conversation starters and exercises.
        </p>
        <ul className="mt-3 list-disc space-y-1 ps-5 text-ink-muted">
          <li>No scores, answers, journal entries or coach conversations are shared.</li>
          <li>There is no compatibility score, and nothing predicts how a relationship will go.</li>
          <li>Either of you can end it at any time, and then neither of you can see it.</li>
        </ul>
      </Card>
      <form onSubmit={accept} className="space-y-4">
        <label className="flex gap-3">
          <input
            type="checkbox"
            className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
          />
          <span>
            I agree to show {otherName(preview.inviter_name, preview.relation_type)} whether each of my Big Five traits
            from my latest result is lower, middle or higher.
          </span>
        </label>
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy}>
            {busy ? "Accepting…" : "Accept invitation"}
          </Button>
          <ButtonLink href="/relationships" variant="secondary">
            Not now
          </ButtonLink>
        </div>
      </form>
    </div>
  );
}
