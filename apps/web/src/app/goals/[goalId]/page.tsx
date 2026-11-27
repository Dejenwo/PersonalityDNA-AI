"use client";

import type { Goal } from "@pdna/api-client";
import { useParams, useRouter } from "next/navigation";
import { type FormEvent, useState } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { formatEntryDate } from "@/lib/journal";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function GoalPage() {
  const { goalId } = useParams<{ goalId: string }>();
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(() => (signedIn ? api.goal(goalId) : Promise.resolve(null)), `${goalId}:${signedIn}`);

  if (!signedIn || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the goal" />;
  if (data.status === "error")
    return (
      <ErrorState level={1}
        title={isNotFound(data.error) ? "Goal not found" : "We couldn't load this goal"}
        message={isNotFound(data.error) ? "It may have been deleted." : errorMessage(data.error)}
        action={<ButtonLink href="/goals">All goals</ButtonLink>}
      />
    );
  return <GoalView key={goalId} initial={data.data!} />;
}

function GoalView({ initial }: { initial: Goal }) {
  const router = useRouter();
  const [g, setG] = useState(initial);
  const [editing, setEditing] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function act(fn: () => Promise<Goal | void>) {
    setBusy(true);
    setError(null);
    try {
      const out = await fn();
      if (out) setG(out);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  // Optimistic, so the checkbox responds at once; the server's version replaces it, or it is put back on error.
  function toggleMilestone(id: string, done: boolean) {
    const before = g;
    const now = new Date().toISOString();
    setG({
      ...g,
      milestones: g.milestones.map((m) => (m.id === id ? { ...m, done_at: done ? now : null } : m)),
      milestones_done: g.milestones_done + (done ? 1 : -1),
    });
    void act(async () => {
      try {
        return await api.updateMilestone(g.id, id, { done });
      } catch (err) {
        setG(before);
        throw err;
      }
    });
  }

  const status = g.status === "active" ? "Active" : g.status === "completed" ? "Completed" : "Archived";

  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <ButtonLink href="/goals" variant="ghost" className="-ms-5">
          ← Goals and habits
        </ButtonLink>
        <p className="text-sm text-ink-muted">
          {status}
          {g.target_date ? ` · target ${formatEntryDate(g.target_date)}` : ""}
        </p>
        <h1 className="text-3xl font-bold">{g.title}</h1>
        {g.why && <p className="mt-2 text-ink-muted">Why it matters: {g.why}</p>}
      </header>

      {editing ? (
        <EditGoal
          g={g}
          onSaved={(out) => {
            setG(out);
            setEditing(false);
          }}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <div className="flex flex-wrap gap-3">
          <Button variant="secondary" onClick={() => setEditing(true)}>
            Adjust goal
          </Button>
          {g.status === "active" ? (
            <>
              <Button onClick={() => act(() => api.updateGoal(g.id, { status: "completed" }))} disabled={busy}>
                Mark goal complete
              </Button>
              <Button variant="ghost" onClick={() => act(() => api.updateGoal(g.id, { status: "archived" }))} disabled={busy}>
                Archive
              </Button>
            </>
          ) : (
            <Button variant="secondary" onClick={() => act(() => api.updateGoal(g.id, { status: "active" }))} disabled={busy}>
              Make active again
            </Button>
          )}
        </div>
      )}

      <Card as="section" aria-labelledby="milestones-heading">
        <h2 id="milestones-heading" className="text-xl font-semibold">
          Milestones
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          {g.milestones.length > 0 ? `${g.milestones_done} of ${g.milestones.length} done` : "Break the goal into a few steps."}
        </p>
        <ul className="mt-3 space-y-2">
          {g.milestones.map((m) => (
            <li key={m.id} className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line p-3">
              <label className="flex items-center gap-3">
                <input
                  type="checkbox"
                  checked={m.done_at !== null}
                  disabled={busy}
                  onChange={(e) => toggleMilestone(m.id, e.target.checked)}
                />
                <span className={m.done_at ? "line-through" : ""}>{m.title}</span>
                {m.due_date && <span className="text-sm text-ink-muted">by {formatEntryDate(m.due_date)}</span>}
              </label>
              <Button variant="ghost" onClick={() => act(() => api.deleteMilestone(g.id, m.id))} disabled={busy}>
                Remove<span className="sr-only"> milestone {m.title}</span>
              </Button>
            </li>
          ))}
        </ul>
        <AddMilestone onAdd={(title, due) => act(() => api.addMilestone(g.id, title, due))} busy={busy} />
      </Card>

      <Card as="section" aria-labelledby="reflect-heading">
        <h2 id="reflect-heading" className="text-xl font-semibold">
          Reflect
        </h2>
        <p className="mt-1 text-ink-muted">
          {g.habits.length > 0
            ? `${g.habits.length} habit${g.habits.length === 1 ? " supports" : "s support"} this goal. `
            : "Add a habit on the goals page to make steady progress. "}
          A short reflection can help you notice what is working.
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <ButtonLink href="/journal/new?kind=goal" variant="secondary">
            Write a goal reflection
          </ButtonLink>
          <ButtonLink href="/coach?topic=goals" variant="secondary">
            Talk it through with the coach
          </ButtonLink>
        </div>
      </Card>

      {error && <FormMessage kind="error">{error}</FormMessage>}

      {confirmDelete ? (
        <div className="rounded-card border border-line p-4" role="group" aria-label="Confirm deletion">
          <p>Delete this goal and its milestones? Habits linked to it are kept.</p>
          <div className="mt-3 flex flex-wrap gap-3">
            <Button
              onClick={() =>
                act(async () => {
                  await api.deleteGoal(g.id);
                  router.push("/goals");
                })
              }
              disabled={busy}
            >
              Yes, delete the goal
            </Button>
            <Button variant="secondary" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : (
        <Button variant="ghost" onClick={() => setConfirmDelete(true)}>
          Delete goal
        </Button>
      )}
    </div>
  );
}

function AddMilestone({ onAdd, busy }: { onAdd: (title: string, due: string | null) => Promise<void>; busy: boolean }) {
  const [title, setTitle] = useState("");
  const [due, setDue] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!title.trim()) return;
    await onAdd(title.trim(), due || null);
    setTitle("");
    setDue("");
  }
  return (
    <form onSubmit={submit} className="mt-4 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
      <TextField id="milestone-title" label="New milestone" value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
      <TextField id="milestone-due" label="Due (optional)" type="date" value={due} onChange={(e) => setDue(e.target.value)} />
      <Button type="submit" variant="secondary" disabled={busy || !title.trim()}>
        Add milestone
      </Button>
    </form>
  );
}

function EditGoal({ g, onSaved, onCancel }: { g: Goal; onSaved: (g: Goal) => void; onCancel: () => void }) {
  const [title, setTitle] = useState(g.title);
  const [why, setWhy] = useState(g.why ?? "");
  const [target, setTarget] = useState(g.target_date ?? "");
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
      onSaved(await api.updateGoal(g.id, { title: title.trim(), why: why.trim() || null, target_date: target || null }));
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="edit-heading">
      <h2 id="edit-heading" className="text-xl font-semibold">
        Adjust goal
      </h2>
      <form onSubmit={submit} className="mt-3 space-y-4" noValidate>
        <TextField id="edit-title" label="Goal" value={title} maxLength={200} onChange={(e) => setTitle(e.target.value)} />
        <TextField id="edit-why" label="Why it matters to you (optional)" value={why} maxLength={1000} onChange={(e) => setWhy(e.target.value)} />
        <TextField id="edit-target" label="Target date (optional)" type="date" value={target} onChange={(e) => setTarget(e.target.value)} />
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <div className="flex flex-wrap gap-3">
          <Button type="submit" disabled={busy}>
            Save changes
          </Button>
          <Button type="button" variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </form>
    </Card>
  );
}
