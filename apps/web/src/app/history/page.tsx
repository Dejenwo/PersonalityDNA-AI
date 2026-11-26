"use client";

import type { HistoryItem } from "@pdna/api-client";
import Link from "next/link";
import { useEffect, useMemo, useState, useSyncExternalStore } from "react";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";
import { parseSessions, rawSessions, subscribeSessions, type StoredSession } from "@/lib/session-store";

const date = (iso: string) => new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });

function Row({ title, subtitle, href, done }: { title: string; subtitle: string; href: string; done: boolean }) {
  return (
    <li>
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="font-semibold">{title}</p>
          <p className="text-sm text-ink-muted">{subtitle}</p>
        </div>
        {done ? (
          <ButtonLink href={href} variant="secondary">View results</ButtonLink>
        ) : (
          <ButtonLink href={href}>Resume</ButtonLink>
        )}
      </Card>
    </li>
  );
}

function AccountHistory() {
  const [state, setState] = useState<{ items?: HistoryItem[]; error?: unknown; n: number }>({ n: 0 });
  useEffect(() => {
    let alive = true;
    api.history().then(
      (r) => alive && setState((s) => ({ items: r.items, n: s.n })),
      (error: unknown) => alive && setState((s) => ({ error, n: s.n })),
    );
    return () => {
      alive = false;
    };
  }, [state.n]);

  if (state.error) {
    return (
      <ErrorState title="We couldn't load your history" message={errorMessage(state.error)}
        action={<Button onClick={() => setState((s) => ({ n: s.n + 1 }))}>Try again</Button>} />
    );
  }
  if (!state.items) return <LoadingState label="Loading your history" />;
  if (state.items.length === 0) {
    return (
      <EmptyState title="No assessments yet" message="Your completed assessments will appear here."
        action={<ButtonLink href="/discover">Start an assessment</ButtonLink>} />
    );
  }
  return (
    <ul className="mt-6 space-y-3">
      {state.items.map((h) => (
        <Row key={h.session_id} title={h.instrument_name}
          subtitle={`Started ${date(h.started_at)} · ${h.result_id
            ? `Completed${h.primary_archetype ? ` · ${h.primary_archetype}` : ""}`
            : `In progress (${h.answered} of ${h.total})`}`}
          href={h.result_id ? `/results/${h.result_id}` : `/assessment/${h.session_id}`} done={Boolean(h.result_id)} />
      ))}
    </ul>
  );
}

function DeviceHistory({ sessions }: { sessions: StoredSession[] }) {
  if (sessions.length === 0) {
    return (
      <EmptyState title="Nothing here yet" message="When you start an assessment, you can come back to it here."
        action={<ButtonLink href="/discover">Start an assessment</ButtonLink>} />
    );
  }
  return (
    <ul className="mt-6 space-y-3">
      {sessions.map((s) => (
        <Row key={s.sessionId} title={s.instrumentName}
          subtitle={`Started ${date(s.startedAt)} · ${s.resultId ? "Completed" : "In progress"}`}
          href={s.resultId ? `/results/${s.resultId}` : `/assessment/${s.sessionId}`} done={Boolean(s.resultId)} />
      ))}
    </ul>
  );
}

export default function HistoryPage() {
  const { state } = useAuth();
  // Server render has no storage: null shows the loading state until the client hydrates.
  const raw = useSyncExternalStore(subscribeSessions, () => rawSessions(), () => null);
  const sessions = useMemo(() => (raw === null ? null : parseSessions(raw)), [raw]);

  return (
    <>
      <h1 className="text-3xl font-bold">My results</h1>
      {state.status === "signed-in" ? (
        <>
          <p className="mt-2 text-ink-muted">Everything saved to your account, on any device.</p>
          <AccountHistory />
        </>
      ) : state.status === "loading" || sessions === null ? (
        <LoadingState />
      ) : (
        <>
          <p className="mt-2 text-ink-muted">
            Assessments you started on this device.{" "}
            <Link href="/register" className="text-primary underline">Create an account</Link> to keep them across devices.
          </p>
          <DeviceHistory sessions={sessions} />
        </>
      )}
    </>
  );
}
