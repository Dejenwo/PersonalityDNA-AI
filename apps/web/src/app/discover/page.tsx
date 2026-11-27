"use client";

import type { AssessmentSummary } from "@pdna/api-client";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useAsync } from "@/lib/use-async";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { TrackView } from "@/components/growth-tracking";

const tierCopy: Record<AssessmentSummary["tier"], { label: string; blurb: string }> = {
  quick: { label: "Quick Discovery", blurb: "A short first look at your Big Five profile. Free." },
  comprehensive: {
    label: "Comprehensive Discovery",
    blurb: "A fuller Big Five assessment with more items per trait, for a steadier picture.",
  },
  advanced: { label: "Advanced Discovery", blurb: "Multiple modules for a deeper profile." },
};

const interestCopy = {
  label: "Career Interests",
  blurb: "Choose the work activities you would like to do, then explore occupations that match your interest areas.",
};

const leadershipCopy = {
  label: "Leadership Preferences",
  blurb: "See which parts of leading you enjoy most and least, then pick development modules to practise.",
};

const copyFor = (a: AssessmentSummary) =>
  a.family === "interests" ? interestCopy : a.family === "leadership" ? leadershipCopy : tierCopy[a.tier];

export default function DiscoverPage() {
  const state = useAsync(() => api.listAssessments(), "assessments");
  return (
    <>
      <TrackView event="assessment_intro_view" />
      <h1 className="text-3xl font-bold">Discover</h1>
      <p className="mt-2 max-w-2xl text-ink-muted">
        Choose an assessment. Answer honestly and describe yourself as you generally are, not as you wish to be.
      </p>
      {state.status === "loading" && <LoadingState label="Loading assessments" />}
      {state.status === "error" && (
        <ErrorState
          title="We couldn't load assessments"
          message={errorMessage(state.error)}
          action={<Button onClick={state.reload}>Try again</Button>}
        />
      )}
      {state.status === "success" && state.data.items.length === 0 && (
        <EmptyState title="No assessments yet" message="Assessments will appear here when they are published." />
      )}
      {state.status === "success" && state.data.items.length > 0 && (
        <ul className="mt-6 grid gap-4 sm:grid-cols-2">
          {state.data.items.map((a) => (
            <li key={a.id}>
              <Card as="article" className="flex h-full flex-col">
                <p className="flex flex-wrap items-center gap-2 text-sm font-semibold text-accent">
                  {copyFor(a).label}
                  {a.status === "draft" && (
                    <span className="rounded-full border border-line px-2 py-0.5 text-xs text-ink-muted">Preview</span>
                  )}
                </p>
                <h2 className="mt-1 text-xl font-semibold">{a.name}</h2>
                <p className="mt-2 flex-1 text-ink-muted">{copyFor(a).blurb}</p>
                <p className="mt-4 text-sm text-ink-muted">
                  {a.item_count} {a.family === "interests" ? "activities" : "statements"} · about {a.estimated_minutes}{" "}
                  minutes
                </p>
                <ButtonLink href={`/discover/${a.id}`} className="mt-4 self-start" aria-label={`Start ${a.name}`}>
                  Start
                </ButtonLink>
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
