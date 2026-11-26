"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { api, PRIVACY_POLICY_VERSION } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { saveSession } from "@/lib/session-store";
import { useAsync } from "@/lib/use-async";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";

export default function AssessmentIntroPage() {
  const { instrumentId } = useParams<{ instrumentId: string }>();
  const router = useRouter();
  const state = useAsync(() => api.getAssessment(instrumentId), instrumentId);
  const [adult, setAdult] = useState(false);
  const [consent, setConsent] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (state.status === "loading") return <LoadingState label="Loading assessment" />;
  if (state.status === "error") {
    return (
      <ErrorState
        title={isNotFound(state.error) ? "Assessment not found" : "We couldn't load this assessment"}
        message={isNotFound(state.error) ? "It may have been retired." : errorMessage(state.error)}
        action={<ButtonLink href="/discover">Back to Discover</ButtonLink>}
      />
    );
  }
  const a = state.data;

  async function start(e: FormEvent) {
    e.preventDefault();
    if (!adult || !consent) return;
    setSubmitting(true);
    setError(null);
    try {
      const res = await api.createSession({
        instrument_id: a.id,
        locale: "en",
        consent: { accepted: true, age_confirmed_18_plus: true, policy_version: PRIVACY_POLICY_VERSION },
      });
      const stored = saveSession({
        sessionId: res.session.id,
        token: res.resume_token,
        instrumentId: a.id,
        instrumentName: a.name,
        startedAt: res.session.started_at,
      });
      if (!stored) {
        setError(
          "Your browser is blocking local storage, so you won't be able to resume later if you leave. You can still finish now.",
        );
      }
      // Token travels in the URL fragment, which browsers never send to servers.
      router.push(`/assessment/${res.session.id}#t=${encodeURIComponent(res.resume_token)}`);
    } catch (err) {
      setError(errorMessage(err));
      setSubmitting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl">
      <Link href="/discover" className="text-sm text-primary underline">
        ← All assessments
      </Link>
      <h1 className="mt-4 text-3xl font-bold">{a.name}</h1>
      <p className="mt-2 text-ink-muted">
        {a.item_count} {a.family === "interests" ? "activities" : "statements"} · about {a.estimated_minutes} minutes · your progress saves automatically
      </p>
      <Card className="mt-6">
        <h2 className="text-lg font-semibold">Before you begin</h2>
        <p className="mt-2">{a.instructions}</p>
        {a.family === "interests" ? (
          <>
            <p className="mt-3 text-sm text-ink-muted">
              Results show which kinds of work activities appeal to you. They describe interests, not abilities, and are
              not compared with other people.
            </p>
            <p className="mt-2 text-xs text-ink-muted">
              This assessment uses the {a.source.name} from the O*NET Career Exploration Tools by the U.S. Department of
              Labor, Employment and Training Administration (USDOL/ETA), used under the CC BY-ND 4.0 licence. O*NET® is a
              trademark of USDOL/ETA. PersonalityDNA is not affiliated with or endorsed by USDOL/ETA.
            </p>
          </>
        ) : (
          <p className="mt-3 text-sm text-ink-muted">
            Source: {a.source.name} ({a.source.authors}). Results describe tendencies in how you see yourself. They are
            not a diagnosis and are not compared with other people.
          </p>
        )}
        {a.status === "draft" && (
          <p className="mt-3 rounded-card border border-line p-3 text-sm">
            Preview: this assessment&apos;s wording is still being checked against the official source.
          </p>
        )}
      </Card>
      <form onSubmit={start} className="mt-6 space-y-4" aria-describedby={error ? "start-error" : undefined}>
        <fieldset className="space-y-3">
          <legend className="sr-only">Consent</legend>
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
              checked={adult}
              onChange={(e) => setAdult(e.target.checked)}
              required
            />
            <span>I confirm I am 18 or older.</span>
          </label>
          <label className="flex items-start gap-3">
            <input
              type="checkbox"
              className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
              required
            />
            <span>
              I agree that PersonalityDNA stores and scores my answers to show me my results, as described in the{" "}
              <Link href="/privacy" className="text-primary underline" target="_blank">
                privacy notice
              </Link>
              .
            </span>
          </label>
        </fieldset>
        {error && (
          <p id="start-error" role="alert" className="text-danger">
            {error}
          </p>
        )}
        <Button type="submit" disabled={!adult || !consent || submitting}>
          {submitting ? "Starting…" : "Begin assessment"}
        </Button>
      </form>
    </div>
  );
}
