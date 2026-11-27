"use client";

import Link from "next/link";
import { ModuleGrid } from "@/components/learning-module";
import { LeadershipAreas, RecommendedModules } from "@/components/result-sections";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { useLatestResults } from "@/lib/latest-results";
import { useAsync } from "@/lib/use-async";

export default function LeadershipPage() {
  const latest = useLatestResults(["leadership"]);
  const signedIn = latest.status === "ready" && latest.signedIn;
  const modules = useAsync(() => api.learningModules("leadership"), `modules:${signedIn}`);

  if (latest.status === "loading" || modules.status === "loading") return <LoadingState label="Loading leadership" />;
  if (latest.status === "error" || modules.status === "error") {
    const error = latest.status === "error" ? latest.error : modules.status === "error" ? modules.error : null;
    return (
      <ErrorState level={1}
        title="We couldn't load leadership development"
        message={errorMessage(error)}
        action={
          <Button
            onClick={() => {
              latest.retry();
              modules.reload();
            }}
          >
            Try again
          </Button>
        }
      />
    );
  }
  const result = latest.results.leadership;
  const instrument = latest.instruments.leadership;
  const list = modules.data;

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl font-bold">Leadership development</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Short modules with practical activities for the people side of leading, whether or not you manage anyone
          today. {list.note}
        </p>
      </header>

      {result?.leadership ? (
        <section aria-labelledby="profile-heading" className="space-y-4">
          <h2 id="profile-heading" className="text-2xl font-bold">
            Suggested for you
          </h2>
          <RecommendedModules leadership={result.leadership} />
          <details className="rounded-card border border-line p-4">
            <summary className="cursor-pointer font-semibold">Your leadership preferences</summary>
            <div className="mt-4">
              <LeadershipAreas leadership={result.leadership} />
            </div>
            <Link href={`/results/${result.id}`} className="mt-3 inline-block text-primary underline">
              See your full leadership results
            </Link>
          </details>
        </section>
      ) : (
        <Card as="section" aria-labelledby="profile-heading">
          <h2 id="profile-heading" className="text-xl font-semibold">
            Find your starting point
          </h2>
          <p className="mt-2 text-ink-muted">
            Answer 27 short statements about which leadership activities you enjoy, and we&apos;ll suggest where to start.
            It takes about 5 minutes.
          </p>
          {instrument && (
            <ButtonLink href={`/discover/${instrument}`} className="mt-4">
              Take the leadership questionnaire
            </ButtonLink>
          )}
        </Card>
      )}

      <ModuleGrid track="leadership" list={list} signedIn={signedIn} />

      <Card>
        <h2 className="text-lg font-semibold">Talk it through</h2>
        <p className="mt-1 text-ink-muted">
          The coach can help you plan a conversation, a delegation or a decision.
        </p>
        <ButtonLink href="/coach?topic=leadership" variant="secondary" className="mt-4">
          Open the coach
        </ButtonLink>
      </Card>
    </div>
  );
}
