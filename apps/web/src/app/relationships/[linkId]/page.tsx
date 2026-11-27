"use client";

import type { LinkDetail, TraitComparison } from "@pdna/api-client";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { capitalize, otherName, relationLabel } from "@/lib/relationships";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

const PATTERN_LABEL: Record<TraitComparison["pattern"], string> = {
  similar: "Similar",
  some_difference: "Some difference",
  different: "Different",
};

export default function RelationshipPage() {
  const { linkId } = useParams<{ linkId: string }>();
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(() => (signedIn ? api.getRelationship(linkId) : Promise.resolve(null)), `${linkId}:${signedIn}`);

  if (!signedIn || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the comparison" />;
  if (data.status === "error")
    return (
      <ErrorState
        title={isNotFound(data.error) ? "Comparison not available" : "We couldn't load this comparison"}
        message={isNotFound(data.error) ? "It may have been ended by either of you." : errorMessage(data.error)}
        action={<ButtonLink href="/relationships">Relationships</ButtonLink>}
      />
    );
  return <Comparison d={data.data!} />;
}

function Comparison({ d }: { d: LinkDetail }) {
  const them = otherName(d.other_name, d.relation_type);
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <ButtonLink href="/relationships" variant="ghost" className="-ms-5">
          ← Relationships
        </ButtonLink>
        <h1 className="text-3xl font-bold">You and {them}</h1>
        <p className="mt-2 text-ink-muted">
          {relationLabel(d.relation_type)}. {d.note}
        </p>
      </header>

      {d.missing_results.length > 0 ? (
        <Card role="note">
          <h2 className="font-semibold">Waiting for results</h2>
          <p className="mt-1 text-ink-muted">
            {d.missing_results.includes("you")
              ? "Take a Big Five assessment to see the comparison."
              : `${capitalize(them)} hasn't taken a Big Five assessment yet. The comparison will appear when they do.`}
          </p>
          {d.missing_results.includes("you") && (
            <ButtonLink href="/discover/mini-ipip-20" className="mt-4">
              Take the quick assessment
            </ButtonLink>
          )}
        </Card>
      ) : (
        <section aria-labelledby="traits-heading" className="space-y-4">
          <h2 id="traits-heading" className="text-2xl font-bold">
            How you each described yourselves
          </h2>
          <p className="text-sm text-ink-muted">
            Based on each person&apos;s latest Big Five result. Only lower, middle and higher bands are compared.
          </p>
          {d.traits.map((t) => (
            <TraitCard key={t.trait} t={t} them={them} />
          ))}
        </section>
      )}

      <section aria-labelledby="exercises-heading" className="space-y-4">
        <h2 id="exercises-heading" className="text-2xl font-bold">
          Try together
        </h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {d.exercises.map((e) => (
            <Card key={e.title} as="article">
              <h3 className="font-semibold">{e.title}</h3>
              <ol className="mt-2 list-decimal space-y-1 ps-5 text-sm text-ink-muted">
                {e.steps.map((s) => (
                  <li key={s}>{s}</li>
                ))}
              </ol>
            </Card>
          ))}
        </div>
        <Card>
          <h3 className="font-semibold">Shared goals to consider</h3>
          <ul className="mt-2 list-disc space-y-1 ps-5 text-ink-muted">
            {d.shared_goals.map((g) => (
              <li key={g}>{g}</li>
            ))}
          </ul>
        </Card>
      </section>

      <EndComparison id={d.id} them={them} />
    </div>
  );
}

function TraitCard({ t, them }: { t: TraitComparison; them: string }) {
  return (
    <Card as="article">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-lg font-semibold">{t.name}</h3>
        <span className="rounded-full border border-line px-2 py-0.5 text-xs text-ink-muted">{PATTERN_LABEL[t.pattern]}</span>
      </div>
      <p className="mt-1 text-sm text-ink-muted">
        You: {t.you} · {capitalize(them)}: {t.them}
      </p>
      <p className="mt-3">{t.summary}</p>
      <p className="mt-2 text-ink-muted">{t.note}</p>
      {t.misunderstanding && (
        <p className="mt-2 text-sm">
          <span className="font-semibold">Possible misunderstanding:</span> {t.misunderstanding}
        </p>
      )}
      <p className="mt-2 text-sm">
        <span className="font-semibold">Talk about it:</span> {t.prompt}
      </p>
    </Card>
  );
}

function EndComparison({ id, them }: { id: string; them: string }) {
  const router = useRouter();
  const [confirm, setConfirm] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function end() {
    setError(null);
    try {
      await api.revokeRelationship(id);
      router.push("/relationships");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Card as="section" aria-labelledby="end-heading">
      <h2 id="end-heading" className="text-lg font-semibold">
        End this comparison
      </h2>
      <p className="mt-1 text-ink-muted">
        Neither of you will be able to see it any more. You can invite {them} again later.
      </p>
      {!confirm ? (
        <Button variant="secondary" className="mt-4" onClick={() => setConfirm(true)}>
          End comparison
        </Button>
      ) : (
        <div role="group" aria-label="Confirm ending the comparison" className="mt-4 flex flex-wrap items-center gap-2">
          <span className="text-sm">End it for both of you?</span>
          <Button onClick={end}>End now</Button>
          <Button variant="secondary" onClick={() => setConfirm(false)}>
            Keep it
          </Button>
        </div>
      )}
      {error && <FormMessage kind="error">{error}</FormMessage>}
    </Card>
  );
}
