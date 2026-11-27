"use client";

import type { ResultOut } from "@pdna/api-client";
import Link from "next/link";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { workingStyleQuestions } from "@/lib/careers";
import { errorMessage } from "@/lib/errors";
import { useLatestResults } from "@/lib/latest-results";

export default function CareersPage() {
  const latest = useLatestResults(["interests", "big_five"]);
  const load =
    latest.status === "ready"
      ? {
          status: "ready" as const,
          interests: latest.results.interests ?? null,
          personality: latest.results.big_five ?? null,
          interestsId: latest.instruments.interests ?? null,
        }
      : latest;
  const signedIn = latest.status === "ready" && latest.signedIn;

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl font-bold">Career exploration</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Bring together the activities that appeal to you and how you tend to work, then explore real occupations. This
          is for reflection: it never tells you which job you are suited for.
        </p>
      </header>
      {load.status === "loading" && <LoadingState label="Loading your results" />}
      {load.status === "error" && (
        <ErrorState
          title="We couldn't load your results"
          message={errorMessage(load.error)}
          action={<Button onClick={latest.retry}>Try again</Button>}
        />
      )}
      {load.status === "ready" && (
        <>
          <InterestsPanel result={load.interests} instrumentId={load.interestsId} />
          <WorkingStylePanel result={load.personality} />
          <Card as="section" aria-labelledby="next-steps">
            <h2 id="next-steps" className="text-xl font-semibold">
              Next steps
            </h2>
            <ul className="mt-2 list-disc space-y-1 ps-5 text-ink-muted">
              <li>Pick two or three occupations that sound interesting and read what the work involves day to day.</li>
              <li>Talk to someone who does that work, or try a short course or volunteering role in the area.</li>
              <li>Notice which activities you look forward to, and which ones drain you.</li>
            </ul>
            <div className="mt-4 flex flex-wrap gap-3">
              {signedIn ? (
                <ButtonLink href="/coach?topic=career" variant="secondary">
                  Explore with the coach
                </ButtonLink>
              ) : (
                <ButtonLink href="/login?next=%2Fcoach%3Ftopic%3Dcareer" variant="secondary">
                  Sign in to explore with the coach
                </ButtonLink>
              )}
            </div>
          </Card>
          <p className="text-sm text-ink-muted">
            Interests describe preferences, not abilities, and personality scores do not predict job performance. Do not
            use these results to make hiring or selection decisions about anyone.
          </p>
        </>
      )}
    </div>
  );
}

function InterestsPanel({ result, instrumentId }: { result: ResultOut | null; instrumentId: string | null }) {
  const interests = result?.interests;
  if (!result || !interests) {
    return (
      <Card as="section" aria-labelledby="interests-heading">
        <h2 id="interests-heading" className="text-xl font-semibold">
          Your career interests
        </h2>
        <p className="mt-2 text-ink-muted">
          You haven&apos;t taken the career interest assessment yet. It asks which of 60 work activities you would like to
          do and takes about 10 minutes.
        </p>
        {instrumentId && (
          <ButtonLink href={`/discover/${instrumentId}`} className="mt-4">
            Take the interest assessment
          </ButtonLink>
        )}
      </Card>
    );
  }
  const top = interests.areas.slice(0, 3);
  return (
    <Card as="section" aria-labelledby="interests-heading">
      <h2 id="interests-heading" className="text-xl font-semibold">
        Your career interests: {interests.empty ? "no clear areas yet" : `code ${interests.code}`}
      </h2>
      {interests.draft && (
        <p className="mt-1 text-sm text-ink-muted">Preview: this assessment&apos;s wording is still being checked.</p>
      )}
      {interests.empty ? (
        <p className="mt-2 text-ink-muted">You didn&apos;t choose any activities, so there is nothing to rank yet.</p>
      ) : (
        <ul className="mt-3 grid gap-3 sm:grid-cols-3">
          {top.map((a) => (
            <li key={a.area} className="rounded-card border border-line p-3">
              <p className="font-semibold">
                {a.name} <span className="text-ink-muted">({a.count} of {a.total})</span>
              </p>
              <p className="mt-1 text-sm text-ink-muted">Fields to explore: {a.fields.slice(0, 3).join(", ")}.</p>
            </li>
          ))}
        </ul>
      )}
      {interests.boundary_ties.length > 0 && !interests.empty && (
        <p className="mt-3 text-sm text-ink-muted">{interests.boundary_ties.join(", ")} are tied around third place.</p>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link href={`/results/${result.id}`} className="text-primary underline">
          See your full interest results
        </Link>
        {interests.explore_links.map((l) => (
          <a key={l.url} className="text-primary underline" href={l.url} target="_blank" rel="noopener noreferrer">
            {l.label}
          </a>
        ))}
      </div>
      <p className="mt-3 text-xs text-ink-muted">{result.methodology.attribution}</p>
    </Card>
  );
}

function WorkingStylePanel({ result }: { result: ResultOut | null }) {
  if (!result) {
    return (
      <Card as="section" aria-labelledby="style-heading">
        <h2 id="style-heading" className="text-xl font-semibold">
          Your working style
        </h2>
        <p className="mt-2 text-ink-muted">
          Take a Big Five personality assessment to add reflection questions about how you like to work.
        </p>
        <ButtonLink href="/discover" className="mt-4" variant="secondary">
          Browse assessments
        </ButtonLink>
      </Card>
    );
  }
  const questions = workingStyleQuestions(result.traits);
  return (
    <Card as="section" aria-labelledby="style-heading">
      <h2 id="style-heading" className="text-xl font-semibold">
        Your working style
      </h2>
      <p className="mt-2 text-ink-muted">
        From your Big Five results ({result.methodology.instrument_name}):{" "}
        {result.traits
          .filter((t) => t.band)
          .map((t) => `${t.name} ${t.band}`)
          .join(", ")}
        . These describe how you see yourself, not what you can do.
      </p>
      <h3 className="mt-4 font-semibold">Questions to reflect on</h3>
      {questions.length > 0 ? (
        <ul className="mt-2 list-disc space-y-1 ps-5">
          {questions.map((q) => (
            <li key={q}>{q}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-ink-muted">
          Your scores sit in the middle band, so think about which settings bring out your more outgoing or quieter,
          planned or flexible sides.
        </p>
      )}
      <Link href={`/results/${result.id}`} className="mt-4 inline-block text-primary underline">
        See your full personality results
      </Link>
    </Card>
  );
}
