"use client";

import type { RelationshipsOut, RelationType } from "@pdna/api-client";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { FormMessage } from "@/components/form";
import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { capitalize, inviteLink, otherName, RELATION_TYPES, relationLabel } from "@/lib/relationships";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

const date = (iso: string) => new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });

export default function RelationshipsPage() {
  const auth = useRequireSignIn();
  const userId = auth.status === "signed-in" ? auth.user.id : "";
  const data = useAsync(() => (userId ? api.relationships() : Promise.resolve(null)), userId);
  // Kept here so the one-time link survives the list reloading after it is created.
  const [created, setCreated] = useState<string | null>(null);

  if (auth.status !== "signed-in" || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading your relationships" />;
  if (data.status === "error")
    return (
      <ErrorState level={1}
        title="We couldn't load your relationships"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  return <Relationships data={data.data!} reload={data.reload} created={created} setCreated={setCreated} />;
}

function Relationships({
  data,
  reload,
  created,
  setCreated,
}: {
  data: RelationshipsOut;
  reload: () => void;
  created: string | null;
  setCreated: (link: string) => void;
}) {
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <header>
        <h1 className="text-3xl font-bold">Relationships</h1>
        <p className="mt-2 text-ink-muted">
          Invite a partner, friend, family member or colleague to compare how you each described yourselves. You get
          conversation starters and exercises, never a compatibility score. Either of you can end it at any time.
        </p>
      </header>

      <Invite
        policyVersion={data.policy_version}
        link={created}
        onCreated={(link) => {
          setCreated(link);
          reload();
        }}
      />

      <section aria-labelledby="links-heading">
        <h2 id="links-heading" className="text-xl font-semibold">
          People you compare with
        </h2>
        {data.links.length === 0 ? (
          <EmptyState title="No one yet" message="When someone accepts your invitation, they will appear here." />
        ) : (
          <ul className="mt-4 space-y-3">
            {data.links.map((l) => (
              <li key={l.id}>
                <Link
                  href={`/relationships/${l.id}`}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line bg-surface p-4 hover:bg-muted"
                >
                  <span>
                    <span className="block font-semibold">{capitalize(otherName(l.other_name, l.relation_type))}</span>
                    <span className="text-sm text-ink-muted">
                      {relationLabel(l.relation_type)} · since {date(l.created_at)}
                    </span>
                  </span>
                  <span className="text-sm text-primary">View comparison</span>
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>

      {data.invitations.length > 0 && (
        <section aria-labelledby="pending-heading">
          <h2 id="pending-heading" className="text-xl font-semibold">
            Open invitations
          </h2>
          <ul className="mt-4 space-y-3">
            {data.invitations.map((i) => (
              <PendingInvitation key={i.id} id={i.id} type={i.relation_type} expires={i.expires_at} onDone={reload} />
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

function PendingInvitation({ id, type, expires, onDone }: { id: string; type: RelationType; expires: string; onDone: () => void }) {
  const [error, setError] = useState<string | null>(null);
  async function cancel() {
    setError(null);
    try {
      await api.cancelInvitation(id);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    }
  }
  return (
    <li>
      <Card as="div" className="flex flex-wrap items-center justify-between gap-3">
        <span>
          <span className="block font-semibold">{relationLabel(type)} invitation</span>
          <span className="text-sm text-ink-muted">Expires {date(expires)}</span>
        </span>
        <Button variant="secondary" onClick={cancel} aria-label={`Cancel ${relationLabel(type).toLowerCase()} invitation`}>
          Cancel
        </Button>
        {error && <FormMessage kind="error">{error}</FormMessage>}
      </Card>
    </li>
  );
}

function Invite({
  policyVersion,
  link,
  onCreated,
}: {
  policyVersion: string;
  link: string | null;
  onCreated: (link: string) => void;
}) {
  const [type, setType] = useState<RelationType>("partner");
  const [agreed, setAgreed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function create(e: FormEvent) {
    e.preventDefault();
    if (!agreed) {
      setError("Please confirm what will be shared.");
      return;
    }
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const res = await api.createInvitation(type, policyVersion);
      setAgreed(false);
      onCreated(inviteLink(window.location.origin, res.token));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="invite-heading">
      <h2 id="invite-heading" className="text-xl font-semibold">
        Invite someone
      </h2>
      <form onSubmit={create} className="mt-4 space-y-5">
        <fieldset>
          <legend className="font-medium">Who are you inviting?</legend>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {RELATION_TYPES.map((t) => (
              <label
                key={t.id}
                className="flex cursor-pointer items-center gap-3 rounded-card border border-line p-3 has-[:checked]:border-primary has-[:checked]:bg-muted"
              >
                <input type="radio" name="relation" value={t.id} checked={type === t.id} onChange={() => setType(t.id)} />
                <span className="font-medium">{t.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
        <label className="flex gap-3">
          <input
            type="checkbox"
            className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
            checked={agreed}
            onChange={(e) => setAgreed(e.target.checked)}
          />
          <span>
            I agree to show the person who accepts whether each of my Big Five traits from my latest result is lower,
            middle or higher. They won&apos;t see my scores, answers, journal or coach conversations. I can end this at any
            time.
          </span>
        </label>
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Button type="submit" disabled={busy}>
          {busy ? "Creating…" : "Create invitation link"}
        </Button>
      </form>
      {link && (
        <div className="mt-6 space-y-2 rounded-card border border-line p-4">
          <label htmlFor="invite-link" className="font-medium">
            Your invitation link
          </label>
          <p className="text-sm text-ink-muted">
            Send it to one person you trust. It works once and expires in 7 days. We show it only now.
          </p>
          <input
            id="invite-link"
            readOnly
            value={link}
            onFocus={(e) => e.target.select()}
            className="block w-full rounded-card border border-line bg-surface p-3 text-sm text-ink"
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" onClick={copy}>
              Copy link
            </Button>
            <span role="status" className="text-sm text-ink-muted">
              {copied ? "Copied." : ""}
            </span>
          </div>
        </div>
      )}
    </Card>
  );
}
