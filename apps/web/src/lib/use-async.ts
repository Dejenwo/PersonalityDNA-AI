"use client";

import { useEffect, useRef, useState } from "react";

export type AsyncState<T> =
  | { status: "loading" }
  | { status: "success"; data: T }
  | { status: "error"; error: unknown };

/**
 * Runs `fn` whenever `key` changes (and on `reload`). State is tagged with the key it was
 * loaded for, so a stale result is never shown for a new key.
 */
export function useAsync<T>(fn: () => Promise<T>, key: string): AsyncState<T> & { reload: () => void } {
  const [loaded, setLoaded] = useState<{ key: string; value: AsyncState<T> } | null>(null);
  const [attempt, setAttempt] = useState(0);
  const fnRef = useRef(fn);
  useEffect(() => {
    fnRef.current = fn;
  });
  const fullKey = `${key}#${attempt}`;

  useEffect(() => {
    let alive = true;
    fnRef.current().then(
      (data) => alive && setLoaded({ key: fullKey, value: { status: "success", data } }),
      (error: unknown) => alive && setLoaded({ key: fullKey, value: { status: "error", error } }),
    );
    return () => {
      alive = false;
    };
  }, [fullKey]);

  const value: AsyncState<T> = loaded?.key === fullKey ? loaded.value : { status: "loading" };
  return { ...value, reload: () => setAttempt((n) => n + 1) };
}
