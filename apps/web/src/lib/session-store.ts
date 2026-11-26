/**
 * Device-local record of assessment sessions so people can resume without an account.
 * Holds only session ids, resume tokens and instrument names: never answers or scores.
 * Every storage access is wrapped because storage can be unavailable (private mode, blocked).
 */

export interface StoredSession {
  sessionId: string;
  token: string;
  instrumentId: string;
  instrumentName: string;
  startedAt: string;
  resultId?: string;
  /** True once attached to the signed-in account. */
  claimed?: boolean;
}

const KEY = "pdna.sessions.v1";
const MAX = 20;

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

function storage(): KeyValueStore | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

function isStored(x: unknown): x is StoredSession {
  if (typeof x !== "object" || x === null) return false;
  const o = x as Record<string, unknown>;
  return typeof o.sessionId === "string" && typeof o.token === "string" && typeof o.instrumentId === "string";
}

/** Raw stored JSON (stable string, suitable as a useSyncExternalStore snapshot). */
export function rawSessions(store: KeyValueStore | null = storage()): string {
  if (!store) return "[]";
  try {
    return store.getItem(KEY) ?? "[]";
  } catch {
    return "[]";
  }
}

export function parseSessions(raw: string): StoredSession[] {
  try {
    const parsed: unknown = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter(isStored) : [];
  } catch {
    return [];
  }
}

export function readSessions(store: KeyValueStore | null = storage()): StoredSession[] {
  return parseSessions(rawSessions(store));
}

export function subscribeSessions(onChange: () => void): () => void {
  const handler = (e: StorageEvent) => {
    if (e.key === KEY || e.key === null) onChange();
  };
  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
}

function write(list: StoredSession[], store: KeyValueStore | null): boolean {
  if (!store) return false;
  try {
    store.setItem(KEY, JSON.stringify(list.slice(0, MAX)));
    return true;
  } catch {
    return false;
  }
}

export function saveSession(s: StoredSession, store: KeyValueStore | null = storage()): boolean {
  const rest = readSessions(store).filter((x) => x.sessionId !== s.sessionId);
  return write([s, ...rest], store);
}

export function updateSession(
  sessionId: string,
  patch: Partial<StoredSession>,
  store: KeyValueStore | null = storage(),
): void {
  write(
    readSessions(store).map((x) => (x.sessionId === sessionId ? { ...x, ...patch } : x)),
    store,
  );
}

export function findSession(sessionId: string, store: KeyValueStore | null = storage()): StoredSession | undefined {
  return readSessions(store).find((x) => x.sessionId === sessionId);
}

export function findByResult(resultId: string, store: KeyValueStore | null = storage()): StoredSession | undefined {
  return readSessions(store).find((x) => x.resultId === resultId);
}

export function forgetSession(sessionId: string, store: KeyValueStore | null = storage()): void {
  write(
    readSessions(store).filter((x) => x.sessionId !== sessionId),
    store,
  );
}
