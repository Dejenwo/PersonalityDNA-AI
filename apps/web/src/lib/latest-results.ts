"use client";

import type { ResultOut } from "@pdna/api-client";
import { useEffect, useState } from "react";
import { api } from "./api";
import { useAuth } from "./auth";
import { latestByFamily, type Family, type ResultRef } from "./careers";
import { readSessions } from "./session-store";

export type LatestResults =
  | { status: "loading" }
  | { status: "error"; error: unknown }
  | {
      status: "ready";
      signedIn: boolean;
      results: Partial<Record<Family, ResultOut>>;
      /** First published instrument of each family, for "take the assessment" links. */
      instruments: Partial<Record<Family, string>>;
    };

/**
 * The newest result of each requested family: from the account when signed in, otherwise from
 * assessments taken on this device (each unlocked by its own resume token).
 */
export function useLatestResults(wanted: Family[]): LatestResults & { retry: () => void } {
  const { state: auth } = useAuth();
  const [load, setLoad] = useState<LatestResults>({ status: "loading" });
  const [attempt, setAttempt] = useState(0);
  const authReady = auth.status !== "loading";
  const signedIn = auth.status === "signed-in";
  const key = wanted.join(",");

  useEffect(() => {
    if (!authReady) return;
    let alive = true;
    (async () => {
      try {
        const catalogue = await api.listAssessments();
        const families = Object.fromEntries(catalogue.items.map((a) => [a.id, a.family]));
        const instruments: Partial<Record<Family, string>> = {};
        for (const a of catalogue.items) instruments[a.family as Family] ??= a.id;
        const refs: ResultRef[] = signedIn
          ? (await api.history()).items.flatMap((h) =>
              h.result_id ? [{ instrumentId: h.instrument_id, resultId: h.result_id, at: h.completed_at ?? h.started_at }] : [],
            )
          : readSessions().flatMap((s) =>
              s.resultId ? [{ instrumentId: s.instrumentId, resultId: s.resultId, at: s.startedAt, token: s.token }] : [],
            );
        const latest = latestByFamily(refs, families);
        const wantedFamilies = key.split(",") as Family[];
        const fetched = await Promise.all(
          wantedFamilies.map(async (f) => {
            const ref = latest[f];
            return [f, ref ? await api.getResult(ref.resultId, ref.token) : undefined] as const;
          }),
        );
        const results: Partial<Record<Family, ResultOut>> = {};
        for (const [f, r] of fetched) if (r) results[f] = r;
        if (alive) setLoad({ status: "ready", signedIn, results, instruments });
      } catch (error) {
        if (alive) setLoad({ status: "error", error });
      }
    })();
    return () => {
      alive = false;
    };
  }, [authReady, signedIn, attempt, key]);

  return {
    ...load,
    retry: () => {
      setLoad({ status: "loading" });
      setAttempt((n) => n + 1);
    },
  };
}
