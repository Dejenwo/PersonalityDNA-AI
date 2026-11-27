"use client";

import type { ShareCard } from "@pdna/api-client";
import { type FormEvent, useState } from "react";
import { FormMessage } from "@/components/form";
import { PersonalityCard } from "@/components/personality-card";
import { Button, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { cardLink } from "@/lib/share";
import { useAsync } from "@/lib/use-async";

/** Opt-in public cards for one report: create, copy the link, stop sharing. */
export function ShareCards({ reportId, hasProfile }: { reportId: string; hasProfile: boolean }) {
  const loaded = useAsync(() => api.shareCards(), `share:${reportId}`);
  if (loaded.status === "loading") return <LoadingState label="Loading shared cards" />;
  if (loaded.status === "error")
    return (
      <ErrorState
        title="We couldn't load your shared cards"
        message={errorMessage(loaded.error)}
        action={<Button onClick={loaded.reload}>Try again</Button>}
      />
    );
  return (
    <Manager
      reportId={reportId}
      hasProfile={hasProfile}
      initial={loaded.data.cards.filter((c) => c.report_id === reportId)}
    />
  );
}

function Manager({ reportId, hasProfile, initial }: { reportId: string; hasProfile: boolean; initial: ShareCard[] }) {
  const [cards, setCards] = useState(initial);
  const [archetype, setArchetype] = useState(hasProfile);
  const [traits, setTraits] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const c = await api.createShareCard({ report_id: reportId, include_archetype: archetype, include_traits: traits });
      setCards((cur) => [c, ...cur]);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(id: string) {
    setBusy(true);
    setError(null);
    try {
      await api.revokeShareCard(id);
      setCards((cur) => cur.filter((c) => c.id !== id));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function copy(c: ShareCard) {
    try {
      await navigator.clipboard.writeText(cardLink(window.location.origin, c.token));
      setCopied(c.id);
    } catch {
      setCopied(null);
    }
  }

  return (
    <Card as="section" aria-labelledby="share-heading">
      <h2 id="share-heading" className="text-xl font-semibold">
        Share a card
      </h2>
      <p className="mt-1 text-ink-muted">
        A card is a small public summary. Anyone with its link can see it, until you stop sharing. It never shows your
        name, email or scores.
      </p>
      <form onSubmit={create} className="mt-4 space-y-3">
        <fieldset className="space-y-2">
          <legend className="font-medium">Show on the card</legend>
          {hasProfile && (
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={archetype} onChange={(e) => setArchetype(e.target.checked)} />
              Profile name and description
            </label>
          )}
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={traits} onChange={(e) => setTraits(e.target.checked)} />
            Big Five bands (lower, middle or higher)
          </label>
        </fieldset>
        <Button type="submit" disabled={busy || (!traits && !(archetype && hasProfile))}>
          Create a share link
        </Button>
      </form>
      {error && <FormMessage kind="error">{error}</FormMessage>}

      {cards.length > 0 && (
        <ul className="mt-6 space-y-6" aria-label="Shared cards">
          {cards.map((c) => {
            const link = cardLink(typeof window === "undefined" ? "" : window.location.origin, c.token);
            return (
              <li key={c.id} className="space-y-3">
                <PersonalityCard card={c.card} />
                <label htmlFor={`link-${c.id}`} className="block text-sm font-medium">
                  Share link
                </label>
                <input
                  id={`link-${c.id}`}
                  readOnly
                  value={link}
                  onFocus={(e) => e.target.select()}
                  className="block min-h-12 w-full rounded-xl border border-line bg-surface px-3 text-sm text-ink"
                />
                <div className="flex flex-wrap gap-3">
                  <Button variant="secondary" onClick={() => copy(c)} disabled={busy}>
                    {copied === c.id ? "Link copied" : "Copy link"}
                  </Button>
                  <Button variant="ghost" onClick={() => revoke(c.id)} disabled={busy}>
                    Stop sharing
                  </Button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
