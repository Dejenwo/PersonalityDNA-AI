"use client";

import type { PublicCard } from "@pdna/api-client";
import { useEffect, useState } from "react";
import { PersonalityCard } from "@/components/personality-card";
import { ButtonLink, ErrorState, LoadingState } from "@/components/ui";
import { TrackView } from "@/components/growth-tracking";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { tokenFromHash } from "@/lib/share";

type Load =
  | { status: "loading" }
  | { status: "missing" }
  | { status: "error"; error: unknown }
  | { status: "ready"; token: string; card: PublicCard };

export default function SharedCardPage() {
  const [load, setLoad] = useState<Load>({ status: "loading" });

  useEffect(() => {
    let alive = true;
    const token = tokenFromHash(window.location.hash);
    const next: Promise<Load> = token
      ? api.publicCard(token).then(
          (card): Load => ({ status: "ready", token, card }),
          (error: unknown): Load => ({ status: "error", error }),
        )
      : Promise.resolve({ status: "missing" });
    next.then((l) => alive && setLoad(l));
    return () => {
      alive = false;
    };
  }, []);

  if (load.status === "loading") return <LoadingState label="Loading the card" />;
  if (load.status === "missing" || (load.status === "error" && isNotFound(load.error)))
    return (
      <ErrorState level={1}
        title="This card isn't available"
        message="The link may be incomplete, or the person who shared it has stopped sharing."
        action={<ButtonLink href="/discover">Discover your own personality</ButtonLink>}
      />
    );
  if (load.status === "error")
    return <ErrorState level={1} title="We couldn't load this card" message={errorMessage(load.error)} />;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <TrackView event="share_card_view" />
      <h1 className="text-3xl font-bold">A shared personality card</h1>
      <PersonalityCard card={load.card} />
      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/discover">Discover your own personality</ButtonLink>
        <a
          className="inline-flex min-h-12 items-center rounded-full px-4 underline"
          href={api.publicCardImageUrl(load.token)}
          target="_blank"
          rel="noopener noreferrer"
        >
          Open the card as an image
        </a>
      </div>
    </div>
  );
}
