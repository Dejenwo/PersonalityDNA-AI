"use client";

import { findByResult, findSession, updateSession } from "./session-store";

/** Reads a resume token passed in the URL fragment (#t=...) and removes it from the address bar. */
export function takeFragmentToken(): string | null {
  if (typeof window === "undefined") return null;
  const match = /(?:^#|&)t=([^&]+)/.exec(window.location.hash);
  if (!match?.[1]) return null;
  window.history.replaceState(null, "", window.location.pathname + window.location.search);
  try {
    return decodeURIComponent(match[1]);
  } catch {
    return null;
  }
}

export function tokenForSession(sessionId: string): string | null {
  return takeFragmentToken() ?? findSession(sessionId)?.token ?? null;
}

export function tokenForResult(resultId: string): string | null {
  return takeFragmentToken() ?? findByResult(resultId)?.token ?? null;
}

export function rememberResult(sessionId: string, resultId: string): void {
  updateSession(sessionId, { resultId });
}
