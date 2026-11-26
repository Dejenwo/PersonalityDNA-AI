"use client";

import { useMemo, useSyncExternalStore } from "react";
import { ButtonLink, Card, EmptyState, LoadingState } from "@/components/ui";
import { parseSessions, rawSessions, subscribeSessions } from "@/lib/session-store";

export default function HistoryPage() {
  // Server render has no storage: null shows the loading state until the client hydrates.
  const raw = useSyncExternalStore(subscribeSessions, () => rawSessions(), () => null);
  const sessions = useMemo(() => (raw === null ? null : parseSessions(raw)), [raw]);

  return (
    <>
      <h1 className="text-3xl font-bold">My results</h1>
      <p className="mt-2 text-ink-muted">
        Assessments you started on this device. Accounts that keep your history across devices are coming soon.
      </p>
      {sessions === null && <LoadingState />}
      {sessions?.length === 0 && (
        <EmptyState
          title="Nothing here yet"
          message="When you start an assessment, you can come back to it here."
          action={<ButtonLink href="/discover">Start an assessment</ButtonLink>}
        />
      )}
      {sessions && sessions.length > 0 && (
        <ul className="mt-6 space-y-3">
          {sessions.map((s) => (
            <li key={s.sessionId}>
              <Card className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-semibold">{s.instrumentName}</p>
                  <p className="text-sm text-ink-muted">
                    Started{" "}
                    {new Date(s.startedAt).toLocaleDateString(undefined, { dateStyle: "medium" })}
                    {s.resultId ? " · Completed" : " · In progress"}
                  </p>
                </div>
                {s.resultId ? (
                  <ButtonLink href={`/results/${s.resultId}`} variant="secondary">
                    View results
                  </ButtonLink>
                ) : (
                  <ButtonLink href={`/assessment/${s.sessionId}`}>Resume</ButtonLink>
                )}
              </Card>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
