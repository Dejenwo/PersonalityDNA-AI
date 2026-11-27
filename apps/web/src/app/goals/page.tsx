"use client";

import type { Goal, Habit } from "@pdna/api-client";
import Link from "next/link";
import { type FormEvent, useState } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { historyLabel, scheduleLabel, WEEKDAYS } from "@/lib/habits";
import { formatEntryDate, localToday } from "@/lib/journal";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function GoalsPage() {
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const [today] = useState(localToday);
  const data = useAsync(
    () => (signedIn ? Promise.all([api.goals(), api.habits(today)]) : Promise.resolve(null)),
    `goals:${signedIn}`,
  );

  if (!signedIn || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading your goals and habits" />;
  if (data.status === "error")
    return (
      <ErrorState level={1}
        title="We couldn't load your goals and habits"
        message={errorMessage(data.error)}
        action={<Button onClick={data.reload}>Try again</Button>}
      />
    );
  const [goals, habits] = data.data!;
  return <Planner initialGoals={goals.goals} initialHabits={habits.habits} today={today} />;
}

function Planner({ initialGoals, initialHabits, today }: { initialGoals: Goal[]; initialHabits: Habit[]; today: string }) {
  const [goals, setGoals] = useState(initialGoals);
  const [habits, setHabits] = useState(initialHabits);
  const active = habits.filter((h) => !h.archived);
  const archived = habits.filter((h) => h.archived);
  const replaceHabit = (h: Habit) => setHabits((cur) => cur.map((x) => (x.id === h.id ? h : x)));

  return (
    <div className="space-y-10">
      <header>
        <h1 className="text-3xl font-bold">Goals and habits</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Set goals you care about, break them into milestones and build small habits that move them forward. Missing a
          day doesn&apos;t reset anything: pick up again whenever you&apos;re ready.
        </p>
      </header>

      <section aria-labelledby="habits-heading" className="space-y-4">
        <h2 id="habits-heading" className="text-2xl font-bold">
          Habits for {formatEntryDate(today)}
        </h2>
        {active.length === 0 ? (
          <p className="text-ink-muted">No habits yet. Start with something small you could do in a few minutes.</p>
        ) : (
          <ul className="space-y-3">
            {active.map((h) => (
              <li key={h.id}>
                <HabitCard h={h} today={today} goals={goals} onChange={replaceHabit} />
              </li>
            ))}
          </ul>
        )}
        <NewHabit goals={goals} today={today} onCreated={(h) => setHabits((cur) => [...cur, h])} />
        {archived.length > 0 && (
          <details className="rounded-card border border-line p-4">
            <summary className="cursor-pointer font-semibold">Paused habits ({archived.length})</summary>
            <ul className="mt-3 space-y-3">
              {archived.map((h) => (
                <li key={h.id}>
                  <HabitCard
                    h={h}
                    today={today}
                    goals={goals}
                    onChange={replaceHabit}
                    onDeleted={() => setHabits((cur) => cur.filter((x) => x.id !== h.id))}
                  />
                </li>
              ))}
            </ul>
          </details>
        )}
      </section>

      <section aria-labelledby="goals-heading" className="space-y-4">
        <h2 id="goals-heading" className="text-2xl font-bold">
          Goals
        </h2>
        {goals.length === 0 ? (
          <p className="text-ink-muted">No goals yet. A good goal is specific enough that you could tell when it&apos;s done.</p>
        ) : (
          <ul className="grid gap-4 sm:grid-cols-2">
            {goals.map((g) => (
              <li key={g.id}>
                <Link
                  href={`/goals/${g.id}`}
                  className="block h-full rounded-card border border-line bg-surface p-5 hover:bg-muted"
                >
                  <span className="block text-sm text-ink-muted">
                    {g.status === "active" ? "Active" : g.status === "completed" ? "Completed" : "Archived"}
                    {g.target_date ? ` · by ${formatEntryDate(g.target_date)}` : ""}
                  </span>
                  <span className="block text-lg font-semibold">{g.title}</span>
                  <span className="mt-1 block text-sm">
                    {g.milestones.length > 0
                      ? `${g.milestones_done} of ${g.milestones.length} milestones done`
                      : "No milestones yet"}
                    {g.habits.length > 0 ? ` · ${g.habits.length} habit${g.habits.length === 1 ? "" : "s"}` : ""}
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        )}
        <NewGoal onCreated={(g) => setGoals((cur) => [g, ...cur])} />
      </section>
    </div>
  );
}

function HabitCard({
  h,
  today,
  goals,
  onChange,
  onDeleted,
}: {
  h: Habit;
  today: string;
  goals: Goal[];
  onChange: (h: Habit) => void;
  onDeleted?: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const goal = goals.find((g) => g.id === h.goal_id);

  async function act(fn: () => Promise<Habit | void>) {
    setBusy(true);
    setError(null);
    try {
      const out = await fn();
      if (out) onChange(out);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="article">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold">{h.title}</h3>
          <p className="text-sm text-ink-muted">
            {scheduleLabel(h.weekdays)}
            {goal ? ` · for “${goal.title}”` : ""}
            {!h.archived && !h.planned_today ? " · not planned today" : ""}
          </p>
        </div>
        {!h.archived && (
          <Button
            variant={h.done_today ? "secondary" : "primary"}
            onClick={() => act(() => api.setHabitDone(h.id, today, !h.done_today, today))}
            disabled={busy}
            aria-pressed={h.done_today}
          >
            {h.done_today ? `Done today: ${h.title}` : `Mark done today: ${h.title}`}
          </Button>
        )}
      </div>
      <p className="mt-2 text-sm">{historyLabel(h)}</p>
      <details className="mt-2">
        <summary className="cursor-pointer text-sm text-primary">History and settings</summary>
        <HabitGrid h={h} />
        <div className="mt-3 flex flex-wrap gap-3">
          <Button
            variant="secondary"
            onClick={() => act(() => api.updateHabit(h.id, { archived: !h.archived }, today))}
            disabled={busy}
          >
            {h.archived ? "Resume habit" : "Pause habit"}
          </Button>
          {h.archived && onDeleted && (
            <Button
              variant="ghost"
              onClick={() =>
                act(async () => {
                  await api.deleteHabit(h.id);
                  onDeleted();
                })
              }
              disabled={busy}
            >
              Delete habit
            </Button>
          )}
        </div>
      </details>
      {error && <FormMessage kind="error">{error}</FormMessage>}
    </Card>
  );
}

/** Four weeks, Monday to Sunday. Each day is described in text for screen readers. */
function HabitGrid({ h }: { h: Habit }) {
  return (
    <div className="mt-3">
      <ol className="grid grid-cols-7 gap-1" aria-label="Last four weeks">
        {h.grid.map((d) => {
          const label = `${formatEntryDate(d.day)}: ${d.done ? "done" : d.planned ? "planned, not done" : "not planned"}`;
          return (
            <li
              key={d.day}
              title={label}
              className={`flex h-8 items-center justify-center rounded-md border text-xs ${
                d.done ? "border-primary bg-primary text-on-primary" : d.planned ? "border-line" : "border-dashed border-line text-ink-muted"
              }`}
            >
              <span className="sr-only">{label}</span>
              <span aria-hidden>{Number(d.day.slice(8))}</span>
            </li>
          );
        })}
      </ol>
      <p className="mt-1 text-xs text-ink-muted">Filled: done. Solid border: planned. Dashed: not planned.</p>
    </div>
  );
}

function NewHabit({ goals, today, onCreated }: { goals: Goal[]; today: string; onCreated: (h: Habit) => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4, 5, 6]);
  const [goalId, setGoalId] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim() || days.length === 0) {
      setError(!title.trim() ? "Give the habit a name." : "Choose at least one day.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      onCreated(await api.createHabit({ title: title.trim(), weekdays: days, goal_id: goalId || null }, today));
      setTitle("");
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!open)
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Add a habit
      </Button>
    );
  return (
    <Card as="section" aria-labelledby="new-habit-heading">
      <h3 id="new-habit-heading" className="text-lg font-semibold">
        New habit
      </h3>
      <form onSubmit={submit} className="mt-3 space-y-4" noValidate>
        <TextField id="habit-title" label="Habit" hint="For example: read 10 pages." value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
        <fieldset>
          <legend className="font-medium">Days</legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {WEEKDAYS.map((name, i) => (
              <label key={name} className="flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm">
                <input
                  type="checkbox"
                  checked={days.includes(i)}
                  onChange={(e) => setDays((cur) => (e.target.checked ? [...cur, i] : cur.filter((d) => d !== i)))}
                />
                {name}
              </label>
            ))}
          </div>
        </fieldset>
        {goals.some((g) => g.status === "active") && (
          <div>
            <label htmlFor="habit-goal" className="block font-medium">
              Supports a goal (optional)
            </label>
            <select
              id="habit-goal"
              value={goalId}
              onChange={(e) => setGoalId(e.target.value)}
              className="mt-1 block min-h-12 w-full rounded-xl border border-line bg-surface px-3 text-ink"
            >
              <option value="">No goal</option>
              {goals
                .filter((g) => g.status === "active")
                .map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.title}
                  </option>
                ))}
            </select>
          </div>
        )}
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy}>
            Save habit
          </Button>
          <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}

function NewGoal({ onCreated }: { onCreated: (g: Goal) => void }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [why, setWhy] = useState("");
  const [target, setTarget] = useState("");
  const [steps, setSteps] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) {
      setError("Give the goal a name.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const milestones = steps
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean)
        .slice(0, 20)
        .map((t) => ({ title: t.slice(0, 200) }));
      onCreated(await api.createGoal({ title: title.trim(), why: why.trim() || null, target_date: target || null, milestones }));
      setTitle("");
      setWhy("");
      setTarget("");
      setSteps("");
      setOpen(false);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (!open)
    return (
      <Button variant="secondary" onClick={() => setOpen(true)}>
        Add a goal
      </Button>
    );
  return (
    <Card as="section" aria-labelledby="new-goal-heading">
      <h3 id="new-goal-heading" className="text-lg font-semibold">
        New goal
      </h3>
      <form onSubmit={submit} className="mt-3 space-y-4" noValidate>
        <TextField id="goal-title" label="Goal" hint="Specific enough that you could tell when it's done." value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
        <TextField id="goal-why" label="Why it matters to you (optional)" value={why} maxLength={1000} onChange={(e) => setWhy(e.target.value)} />
        <TextField id="goal-target" label="Target date (optional)" type="date" value={target} onChange={(e) => setTarget(e.target.value)} />
        <div>
          <label htmlFor="goal-steps" className="block font-medium">
            Milestones (optional)
          </label>
          <p id="goal-steps-hint" className="text-sm text-ink-muted">
            One per line. You can add or change them later.
          </p>
          <textarea
            id="goal-steps"
            aria-describedby="goal-steps-hint"
            value={steps}
            onChange={(e) => setSteps(e.target.value)}
            rows={4}
            className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
          />
        </div>
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy}>
            Save goal
          </Button>
          <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
