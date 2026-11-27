"use client";

import type { OrgInvitationPreview } from "@pdna/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { ORG_INVITE_KEY } from "@/lib/orgs";
import { captureInviteToken, forgetInviteToken } from "@/lib/relationships";
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
  | { status: "ready"; token: string; preview: OrgInvitationPreview };

export default function JoinOrgPage() {
  // Capture the token before the sign-in redirect can drop the fragment.
  const token = useRef<string | null>(null);
  useEffect(() => {
    token.current = captureInviteToken(window.location, sessionStore(), ORG_INVITE_KEY);
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
      ? api.previewOrgInvitation(t).then(
          (preview): Load => ({ status: "ready", token: t, preview }),
          (error: unknown): Load => {
            if (isNotFound(error)) forgetInviteToken(sessionStore(), ORG_INVITE_KEY);
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
      <ErrorState level={1}
        title={gone ? "This join link isn't available" : "We couldn't load this join link"}
        message={
          gone
            ? "The link may be incomplete, used up, cancelled or expired. Ask the organisation for a new one."
            : errorMessage(load.error)
        }
        action={<ButtonLink href="/orgs">Organisations</ButtonLink>}
      />
    );
  }
  return <Accept token={load.token} preview={load.preview} />;
}

function Accept({ token, preview }: { token: string; preview: OrgInvitationPreview }) {
  const router = useRouter();
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function accept(e: FormEvent) {
    e.preventDefault();
    if (!agreed) {
      setError("Please confirm what the organisation will see.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const org = await api.acceptOrgInvitation(token, preview.policy_version);
      forgetInviteToken(sessionStore(), ORG_INVITE_KEY);
      router.push(`/orgs/${org.id}`);
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">Join {preview.organisation}</h1>
      <Card>
        <p>
          You&apos;re invited as {preview.role === "member" ? "a member" : "an administrator"}. Joining is voluntary and
          you can leave at any time.
        </p>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-ink-muted">
          <li>The organisation sees your name, email, role and when you joined.</li>
          <li>It never sees your answers, results, reports, journal, goals or coach conversations.</li>
          <li>
            Counting your results in anonymous group statistics is a separate choice, off unless you turn it on, and
            only shown for groups of at least 10.
          </li>
          <li>PersonalityDNA must not be used for hiring, promotion, pay or other employment decisions.</li>
        </ul>
      </Card>
      {preview.already_member ? (
        <p>You&apos;re already a member of this organisation.</p>
      ) : (
        <form onSubmit={accept} className="space-y-4">
          <label className="flex gap-3">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
              checked={agreed}
              onChange={(e) => setAgreed(e.target.checked)}
            />
            <span>I agree that {preview.organisation} can see my name, email, role and join date.</span>
          </label>
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <div className="flex flex-wrap gap-3">
            <Button type="submit" disabled={busy}>
              {busy ? "Joining…" : "Join organisation"}
            </Button>
            <ButtonLink href="/orgs" variant="secondary">
              Not now
            </ButtonLink>
          </div>
        </form>
      )}
    </div>
  );
}
