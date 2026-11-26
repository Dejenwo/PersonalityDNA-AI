"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export function AuthNav() {
  const { state } = useAuth();
  if (state.status === "loading") return <li aria-hidden className="w-16" />;
  if (state.status === "signed-in") {
    return (
      <li>
        <Link href="/account" className="rounded-full px-3 py-2 hover:bg-muted">
          Account
        </Link>
      </li>
    );
  }
  return (
    <li>
      <Link href="/login" className="rounded-full px-3 py-2 hover:bg-muted">
        Sign in
      </Link>
    </li>
  );
}
