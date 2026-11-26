"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function AuthNav() {
  const { state } = useAuth();
  if (state.status === "loading") return <li aria-hidden className="w-16" />;
  if (state.status === "signed-in") {
    return (
      <>
        <li>
          <Link href="/coach" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            Coach
          </Link>
        </li>
        <li>
          <Link href="/account" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            Account
          </Link>
        </li>
      </>
    );
  }
  return (
    <li>
      <Link href="/login" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
        Sign in
      </Link>
    </li>
  );
}
