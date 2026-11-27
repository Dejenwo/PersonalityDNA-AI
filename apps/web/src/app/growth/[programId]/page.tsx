"use client";

import type { GrowthProgram } from "@pdna/api-client";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Progress } from "@/components/growth";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage, isNotFound } from "@/lib/errors";
import { allDays, dayTitle, lengthLabel, weekOfDay, withDay, withRating } from "@/lib/growth";
import { useAsync } from "@/lib/use-async";

type Day = GrowthProgram["review_days"][number];
type Week = GrowthProgram["weeks"][number];

export default function ProgramPage() {
  const { programId } = useParams<{ programId: string }>();
  const { state: auth } = useAuth();
  const data = useAsync(
    () => (auth.status === "loading" ? Promise.resolve(null) : api.growthProgram(programId)),
    `${programId}:${auth.status}`,
  );

  if (data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the programme" />;
  if (data.status === "error")
    return (
      <ErrorState level={1}
        title={isNotFound(data.error) ? "Programme not found" : "We couldn't load this programme"}
        message={isNotFound(data.error) ? "It may have been renamed." : errorMessage(data.error)}
        action={<ButtonLink href="/growth">All programmes</ButtonLink>}
      />
    );
  return <Program key={programId} initial={data.data!} signedIn={auth.status === "signed-in"} />;
}

function Program({ initial, signedIn }: { initial: GrowthProgram; signedIn: boolean }) {
  const [p, setP] = useState(initial);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<"restart" | "leave" | null>(null);
  const e = p.enrollment;
  const today = e?.next_day ? allDays(p).find((d) => d.day === e.next_day) : undefined;
  const currentWeek = e?.next_day ? weekOfDay(p, e.next_day) : null;

  async function run(action: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const start = () =>
    run(async () => {
      setP(await api.startProgram(p.id));
      setConfirm(null);
    });
  const leave = () =>
    run(async () => {
      await api.leaveProgram(p.id);
      setP(await api.growthProgram(p.id));
      setConfirm(null);
    });
  const toggleDay = (day: Day) =>
    run(async () => {
      const done = day.completed_at === null;
      await api.setDayDone(p.id, day.day, done);
      setP((cur) => withDay(cur, day.day, done, new Date().toISOString()));
    });
  // Optimistic: the choice shows at once and is put back if saving fails.
  const rate = (week: number, rating: number) => {
    const before = p.weeks.find((w) => w.number === week)?.rating ?? null;
    setP((cur) => withRating(cur, week, rating));
    return run(async () => {
      try {
        await api.setCheckIn(p.id, week, rating);
      } catch (err) {
        setP((cur) => withRating(cur, week, before));
        throw err;
      }
    });
  };

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <ButtonLink href="/growth" variant="ghost" className="-ms-5">
          ← Growth programmes
        </ButtonLink>
        <p className="text-sm text-ink-muted">{lengthLabel(p.days)}</p>
        <h1 className="text-3xl font-bold">{p.title}</h1>
        <p className="mt-2 text-ink-muted">{p.summary}</p>
        <h2 className="mt-4 font-semibold">What you will work on</h2>
        <ul className="mt-1 list-disc space-y-1 ps-5">
          {p.objectives.map((o) => (
            <li key={o}>{o}</li>
          ))}
        </ul>
      </header>

      <Card as="section" aria-labelledby="status-heading">
        <h2 id="status-heading" className="text-xl font-semibold">
          {e ? (e.next_day ? "Your progress" : "Programme finished") : "Start this programme"}
        </h2>
        {!signedIn ? (
          <p className="mt-2 text-ink-muted">
            You can read every day below.{" "}
            <Link href={`/login?next=${encodeURIComponent(`/growth/${p.id}`)}`} className="text-primary underline">
              Sign in
            </Link>{" "}
            to start the programme and keep track of your days.
          </p>
        ) : !e ? (
          <>
            <p className="mt-2 text-ink-muted">
              Aim for one day at a time. If you miss a day, simply pick up where you left off.
            </p>
            <Button className="mt-4" onClick={start} disabled={busy}>
              Start the programme
            </Button>
          </>
        ) : (
          <>
            <Progress done={e.days_done} total={p.days} next={e.next_day} />
            {e.next_day === null && (
              <p className="mt-2 text-ink-muted">Well done. Look back at the reflection questions, or start another programme.</p>
            )}
            {confirm ? (
              <div className="mt-4 rounded-card border border-line p-3" role="group" aria-label="Confirm">
                <p>
                  {confirm === "restart"
                    ? "Start again from day 1? This clears your days and self-checks for this programme."
                    : "Leave this programme? This deletes your days and self-checks for it."}
                </p>
                <div className="mt-3 flex flex-wrap gap-3">
                  <Button onClick={confirm === "restart" ? start : leave} disabled={busy}>
                    {confirm === "restart" ? "Yes, start again" : "Yes, leave"}
                  </Button>
                  <Button variant="secondary" onClick={() => setConfirm(null)} disabled={busy}>
                    Cancel
                  </Button>
                </div>
              </div>
            ) : (
              <div className="mt-4 flex flex-wrap gap-3">
                <Button variant="secondary" onClick={() => setConfirm("restart")}>
                  Start again
                </Button>
                <Button variant="ghost" onClick={() => setConfirm("leave")}>
                  Leave programme
                </Button>
              </div>
            )}
          </>
        )}
        {error && <FormMessage kind="error">{error}</FormMessage>}
      </Card>

      {today && (
        <Card as="section" aria-labelledby="today-heading">
          <h2 id="today-heading" className="text-xl font-semibold">
            Next up: {dayTitle(today)}
          </h2>
          <p className="mt-2">{today.text}</p>
          <Button className="mt-4" onClick={() => toggleDay(today)} disabled={busy}>
            I&apos;ve done today&apos;s exercise
          </Button>
        </Card>
      )}

      <section aria-labelledby="plan-heading" className="space-y-4">
        <h2 id="plan-heading" className="text-2xl font-bold">
          The plan
        </h2>
        {p.weeks.map((w) => (
          <WeekBlock
            key={w.number}
            w={w}
            scale={p.self_evaluation_scale}
            open={currentWeek === w.number || (!e && w.number === 1)}
            enrolled={!!e}
            busy={busy}
            onToggle={toggleDay}
            onRate={(r) => rate(w.number, r)}
          />
        ))}
        {p.review_days.length > 0 && (
          <details className="rounded-card border border-line bg-surface p-4" open={!!e?.next_day && currentWeek === null}>
            <summary className="cursor-pointer text-lg font-semibold">Review days</summary>
            <DayList days={p.review_days} enrolled={!!e} busy={busy} onToggle={toggleDay} />
          </details>
        )}
      </section>

      <p className="text-sm text-ink-muted">{p.note}</p>
    </div>
  );
}

function WeekBlock({
  w,
  scale,
  open,
  enrolled,
  busy,
  onToggle,
  onRate,
}: {
  w: Week;
  scale: string[];
  open: boolean;
  enrolled: boolean;
  busy: boolean;
  onToggle: (d: Day) => void;
  onRate: (rating: number) => void;
}) {
  const done = w.days.filter((d) => d.completed_at !== null).length;
  return (
    <details className="rounded-card border border-line bg-surface p-4" open={open}>
      <summary className="cursor-pointer">
        <span className="text-lg font-semibold">
          Week {w.number}: {w.title}
        </span>
        {enrolled && <span className="ms-2 text-sm text-ink-muted">({done} of 7 days done)</span>}
      </summary>
      <div className="mt-3 space-y-4">
        <p>
          <span className="font-semibold">Objective:</span> {w.objective}
        </p>
        <div>
          <h3 className="font-semibold">{w.lesson_title}</h3>
          <h4 className="mt-2 text-sm font-semibold">{w.practice.title}</h4>
          <ol className="mt-1 list-decimal space-y-1 ps-5 text-ink-muted">
            {w.practice.steps.map((s) => (
              <li key={s}>{s}</li>
            ))}
          </ol>
        </div>
        <DayList days={w.days} enrolled={enrolled} busy={busy} onToggle={onToggle} />
        <fieldset className="rounded-card border border-line p-3">
          <legend className="px-1 font-semibold">Week {w.number} self-check</legend>
          <p className="text-sm">{w.self_evaluation}</p>
          {enrolled ? (
            <div className="mt-2 flex flex-wrap gap-2">
              {scale.map((label, i) => (
                <label key={label} className="flex items-center gap-1 rounded-full border border-line px-3 py-1 text-sm">
                  <input
                    type="radio"
                    name={`week-${w.number}`}
                    checked={w.rating === i + 1}
                    disabled={busy}
                    onChange={() => onRate(i + 1)}
                  />
                  {label}
                </label>
              ))}
            </div>
          ) : (
            <p className="mt-1 text-sm text-ink-muted">Start the programme to record your self-checks.</p>
          )}
          <p className="mt-3 text-sm">
            <span className="font-semibold">To reflect on:</span> {w.reflection}
          </p>
        </fieldset>
      </div>
    </details>
  );
}

function DayList({
  days,
  enrolled,
  busy,
  onToggle,
}: {
  days: Day[];
  enrolled: boolean;
  busy: boolean;
  onToggle: (d: Day) => void;
}) {
  return (
    <ol className="mt-3 space-y-3">
      {days.map((d) => (
        <li key={d.day} className="rounded-card border border-line p-3">
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h3 className="font-semibold">{dayTitle(d)}</h3>
            {d.completed_at && <span className="rounded-full border border-line px-2 py-0.5 text-xs">Done</span>}
          </div>
          <p className="mt-1 text-ink-muted">{d.text}</p>
          {enrolled && (
            <Button variant="secondary" className="mt-2" onClick={() => onToggle(d)} disabled={busy}>
              {d.completed_at ? `Mark day ${d.day} as not done` : `Mark day ${d.day} as done`}
            </Button>
          )}
        </li>
      ))}
    </ol>
  );
}
