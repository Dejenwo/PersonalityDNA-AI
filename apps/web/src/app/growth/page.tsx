"use client";

import type { ProgramSummary } from "@pdna/api-client";
import Link from "next/link";
import { Progress } from "@/components/growth";
import { Button, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";
import { lengthLabel } from "@/lib/growth";
import { useAsync } from "@/lib/use-async";

export default function GrowthPage() {
  const { state: auth } = useAuth();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(
    () => (auth.status === "loading" ? Promise.resolve(null) : api.growthPrograms()),
    `growth:${auth.status}`,
  );

  if (data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading growth programmes" />;
  if (data.status === "error")
    return (
      <ErrorState level={1}
        title="We couldn't load the growth programmes"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  const list = data.data!;
  const mine = list.programs.filter((p) => p.enrollment);
  const challenges = list.programs.filter((p) => p.kind === "challenge");
  const programmes = list.programs.filter((p) => p.kind === "program");

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl font-bold">Growth programmes</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Structured programmes with a short exercise for each day, a milestone at the end of each week and a quick
          self-check on how it went. {list.note}
        </p>
        {!signedIn && (
          <p className="mt-2 text-sm text-ink-muted">
            <Link href="/login?next=%2Fgrowth" className="text-primary underline">
              Sign in
            </Link>{" "}
            to start a programme and keep track of your days.
          </p>
        )}
      </header>

      {mine.length > 0 && (
        <section aria-labelledby="mine-heading" className="space-y-4">
          <h2 id="mine-heading" className="text-2xl font-bold">
            Your programmes
          </h2>
          <ul className="grid gap-4 sm:grid-cols-2">
            {mine.map((p) => (
              <li key={p.id}>
                <ProgramLink p={p} />
              </li>
            ))}
          </ul>
        </section>
      )}

      <ProgramSection id="challenges" title="7-day challenges" programs={challenges} />
      <ProgramSection id="programmes" title="30, 60 and 90-day programmes" programs={programmes} />
    </div>
  );
}

function ProgramSection({ id, title, programs }: { id: string; title: string; programs: ProgramSummary[] }) {
  return (
    <section aria-labelledby={`${id}-heading`} className="space-y-4">
      <h2 id={`${id}-heading`} className="text-2xl font-bold">
        {title}
      </h2>
      <ul className="grid gap-4 sm:grid-cols-2">
        {programs.map((p) => (
          <li key={p.id}>
            <ProgramLink p={p} />
          </li>
        ))}
      </ul>
    </section>
  );
}

function ProgramLink({ p }: { p: ProgramSummary }) {
  const e = p.enrollment;
  return (
    <Link
      href={`/growth/${encodeURIComponent(p.id)}`}
      className="block h-full rounded-card border border-line bg-surface p-5 hover:bg-muted"
    >
      <span className="block text-sm text-ink-muted">{lengthLabel(p.days)}</span>
      <span className="block text-lg font-semibold">{p.title}</span>
      <span className="mt-1 block text-sm text-ink-muted">{p.summary}</span>
      {e && <Progress done={e.days_done} total={p.days} next={e.next_day} />}
    </Link>
  );
}
