"use client";

import type { ArchetypeOut, ResultOut } from "@pdna/api-client";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { TraitBar } from "@/components/trait-bar";
import { ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { tokenForResult } from "@/lib/token";

type Load = { status: "loading" } | { status: "error"; error: unknown; noToken?: boolean } | { status: "ready"; result: ResultOut };

const flagText: Record<string, string> = {
  uniform_responses:
    "You gave the same answer to every statement. Results may not reflect you well; consider retaking it when you have a few quiet minutes.",
  rapid_completion:
    "This assessment was completed very quickly. If you rushed, consider retaking it so the results reflect you more accurately.",
};

function ArchetypeCard({ a, rank }: { a: ArchetypeOut; rank: "Primary" | "Secondary" }) {
  return (
    <Card as="article">
      <p className="text-sm font-semibold text-accent">{rank} archetype</p>
      <h3 className="mt-1 text-2xl font-bold">{a.name}</h3>
      <p className="mt-2">{a.summary}</p>
      {a.drivers.length > 0 && (
        <p className="mt-3 text-sm text-ink-muted">Based on your {a.drivers.join(", ")}.</p>
      )}
      <div className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <h4 className="font-semibold">Possible strengths</h4>
          <ul className="mt-1 list-disc pl-5 text-ink-muted">
            {a.strengths.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="font-semibold">Ideas to grow</h4>
          <ul className="mt-1 list-disc pl-5 text-ink-muted">
            {a.growth.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ul>
        </div>
      </div>
    </Card>
  );
}

export default function ResultsPage() {
  const { resultId } = useParams<{ resultId: string }>();
  const [load, setLoad] = useState<Load>({ status: "loading" });

  useEffect(() => {
    let alive = true;
    (async () => {
      const token = tokenForResult(resultId);
      if (!token) {
        setLoad({ status: "error", error: null, noToken: true });
        return;
      }
      try {
        const result = await api.getResult(resultId, token);
        if (alive) setLoad({ status: "ready", result });
      } catch (error) {
        if (alive) setLoad({ status: "error", error });
      }
    })();
    return () => {
      alive = false;
    };
  }, [resultId]);

  if (load.status === "loading") return <LoadingState label="Loading your results" />;
  if (load.status === "error") {
    const missing = load.noToken || isNotFound(load.error);
    return (
      <ErrorState
        title={missing ? "These results aren't available on this device" : "We couldn't load your results"}
        message={
          missing
            ? "Results are private to the device where the assessment was taken."
            : errorMessage(load.error)
        }
        action={<ButtonLink href="/history">My results</ButtonLink>}
      />
    );
  }

  const r = load.result;
  const m = r.methodology;
  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">Your PersonalityDNA</p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
          {r.archetypes.weak_fit ? "A balanced profile" : r.archetypes.primary.name}
        </h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          {r.archetypes.weak_fit
            ? "Your answers sit close to the middle on most traits, so no single archetype stands out strongly. The closest matches are shown below."
            : `with elements of ${r.archetypes.secondary.name}. These describe tendencies in how you see yourself, not fixed categories.`}
        </p>
      </header>

      {r.quality_flags.length > 0 && (
        <Card role="note" className="border-accent">
          <h2 className="font-semibold">A note about these results</h2>
          <ul className="mt-2 list-disc pl-5 text-ink-muted">
            {r.quality_flags.map((f) => (
              <li key={f}>{flagText[f] ?? f}</li>
            ))}
          </ul>
        </Card>
      )}

      <section aria-labelledby="traits">
        <h2 id="traits" className="text-2xl font-bold">
          Your Big Five traits
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          0 to 100 shows where your answers fall on the response scale. It is not a percentile and does not compare
          you with anyone else.
        </p>
        <Card className="mt-4 space-y-6">
          {r.traits.map((t) => (
            <TraitBar key={t.trait} trait={t} />
          ))}
          {r.negative_emotionality !== null && (
            <p className="text-sm text-ink-muted">
              Negative Emotionality (Neuroticism): {r.negative_emotionality.toFixed(0)} / 100. {m.negative_emotionality_note}
            </p>
          )}
        </Card>
      </section>

      <section aria-labelledby="archetypes" className="space-y-4">
        <h2 id="archetypes" className="text-2xl font-bold">
          Your archetypes
        </h2>
        <p className="text-sm text-ink-muted">{r.archetypes.disclaimer}</p>
        <ArchetypeCard a={r.archetypes.primary} rank="Primary" />
        <ArchetypeCard a={r.archetypes.secondary} rank="Secondary" />
      </section>

      <section aria-labelledby="detail" className="space-y-4">
        <h2 id="detail" className="text-2xl font-bold">
          Trait by trait
        </h2>
        {r.traits.map((t) => (
          <Card key={t.trait} as="article">
            <h3 className="text-lg font-semibold">{t.name}</h3>
            {t.summary && <p className="mt-1">{t.summary}</p>}
            <div className="mt-3 grid gap-4 sm:grid-cols-2">
              <div>
                <h4 className="font-semibold">Possible strengths</h4>
                <ul className="mt-1 list-disc pl-5 text-ink-muted">
                  {t.strengths.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-semibold">Growth opportunities</h4>
                <ul className="mt-1 list-disc pl-5 text-ink-muted">
                  {t.growth.map((s) => (
                    <li key={s}>{s}</li>
                  ))}
                </ul>
              </div>
            </div>
          </Card>
        ))}
      </section>

      <section aria-labelledby="method">
        <h2 id="method" className="text-2xl font-bold">
          How this was calculated
        </h2>
        <Card className="mt-4 space-y-3 text-ink-muted">
          <p>{m.scoring_summary}</p>
          <p>{m.band_note}</p>
          <h3 className="pt-2 font-semibold text-ink">Limitations</h3>
          <ul className="list-disc space-y-1 pl-5">
            {m.limitations.map((l) => (
              <li key={l}>{l}</li>
            ))}
          </ul>
          <details className="pt-2">
            <summary className="cursor-pointer font-semibold text-ink">References and audit details</summary>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm">
              {m.references.map((ref) => (
                <li key={ref}>{ref}</li>
              ))}
            </ul>
            <p className="mt-2 text-sm">{m.attribution}</p>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 text-xs break-all">
              <dt>Instrument</dt>
              <dd>
                {m.instrument_name} ({m.instrument_id} v{m.instrument_version})
              </dd>
              <dt>Scoring engine</dt>
              <dd>v{m.engine_version}</dd>
              <dt>Content hash</dt>
              <dd>{m.content_sha256}</dd>
              <dt>Answers hash</dt>
              <dd>{m.answers_sha256}</dd>
            </dl>
          </details>
        </Card>
      </section>

      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/discover">Take another assessment</ButtonLink>
        <ButtonLink href="/history" variant="secondary">
          My results
        </ButtonLink>
      </div>
    </div>
  );
}
