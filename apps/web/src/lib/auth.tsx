"use client";

import type { UserOut } from "@pdna/api-client";
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api, setAccessToken, setRefresher } from "./api";
import { readSessions, updateSession } from "./session-store";

type AuthState =
  | { status: "loading"; user: null }
  | { status: "signed-out"; user: null }
  | { status: "signed-in"; user: UserOut };

interface AuthContextValue {
  state: AuthState;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  setUser: (user: UserOut) => void;
  /** Clear local auth state without calling the server (after account deletion). */
  forget: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

/** Attach assessments taken on this device (before signing in) to the account. */
async function claimDeviceSessions(): Promise<void> {
  for (const s of readSessions()) {
    if (s.claimed) continue;
    try {
      await api.claimSession(s.sessionId, s.token);
      updateSession(s.sessionId, { claimed: true });
    } catch {
      // Not found (expired, deleted, or owned by someone else): leave it on the device only.
    }
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>({ status: "loading", user: null });
  const inflight = useRef<Promise<string | null> | null>(null);

  const refresh = useCallback((): Promise<string | null> => {
    // Concurrent 401s share one refresh; the server rotates the token on every call.
    inflight.current ??= api
      .refresh()
      .then((res) => {
        setAccessToken(res.access_token);
        setState({ status: "signed-in", user: res.user });
        return res.access_token;
      })
      .catch(() => {
        setAccessToken(null);
        setState({ status: "signed-out", user: null });
        return null;
      })
      .finally(() => {
        inflight.current = null;
      });
    return inflight.current;
  }, []);

  useEffect(() => {
    setRefresher(refresh);
    void refresh().then((token) => {
      if (token) void claimDeviceSessions();
    });
    return () => setRefresher(null);
  }, [refresh]);

  const signIn = useCallback(async (email: string, password: string) => {
    const res = await api.login(email, password);
    setAccessToken(res.access_token);
    setState({ status: "signed-in", user: res.user });
    await claimDeviceSessions();
  }, []);

  const forget = useCallback(() => {
    setAccessToken(null);
    setState({ status: "signed-out", user: null });
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } finally {
      forget();
    }
  }, [forget]);

  const setUser = useCallback((user: UserOut) => setState({ status: "signed-in", user }), []);

  const value = useMemo(() => ({ state, signIn, signOut, setUser, forget }), [state, signIn, signOut, setUser, forget]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
