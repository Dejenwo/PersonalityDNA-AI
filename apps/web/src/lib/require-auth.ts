"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "./auth";

/** Sends signed-out visitors to sign in, then back to the current page. Returns the auth state. */
export function useRequireSignIn() {
  const { state } = useAuth();
  const router = useRouter();
  useEffect(() => {
    if (state.status !== "signed-out") return;
    const here = window.location.pathname + window.location.search;
    router.replace(`/login?next=${encodeURIComponent(here)}`);
  }, [state.status, router]);
  return state;
}
