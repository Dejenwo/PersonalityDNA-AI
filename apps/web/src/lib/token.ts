"use client";

import { findByResult, findSession, updateSession } from "./session-store";

/** Reads a token passed in the URL fragment (#t=... or #token=...) and removes it from the address bar. */
export function takeFragmentToken(name = "t"): string | null {
  if (typeof window === "undefined") return null;
  const match = new RegExp(`(?:^#|&)${name}=([^&]+)`).exec(window.location.hash);
  if (!match?.[1]) return null;
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

/**
 * Per-page holder: the fragment is read the first time and remembered, so effects that run
 * again (e.g. when sign-in state resolves) still see it.
 */
export function createTokenReader() {
  let frag: string | null | undefined;
  const fragment = () => (frag === undefined ? (frag = takeFragmentToken()) : frag);
  return {
    forSession: (sessionId: string) => fragment() ?? findSession(sessionId)?.token ?? null,
    forResult: (resultId: string) => fragment() ?? findByResult(resultId)?.token ?? null,
  };
}

export function rememberResult(sessionId: string, resultId: string): void {
  updateSession(sessionId, { resultId });
}
