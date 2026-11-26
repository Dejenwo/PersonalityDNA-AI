"use client";

import { ApiError } from "@pdna/api-client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";
import { safeNextPath } from "@/lib/next-path";

export default function LoginPage() {
  const { signIn } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [unverified, setUnverified] = useState(false);
  const [resent, setResent] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setUnverified(false);
    try {
      await signIn(email, password);
      router.push(safeNextPath(window.location.search));
    } catch (err) {
      setUnverified(err instanceof ApiError && err.code === "email_unverified");
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  async function resend() {
    await api.resendVerification(email).catch(() => undefined);
    setResent(true);
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-3xl font-bold">Sign in</h1>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <TextField id="email" label="Email" type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <TextField id="password" label="Password" type="password" autoComplete="current-password" required
          value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <FormMessage kind="error">{error}</FormMessage>}
        {unverified &&
          (resent ? (
            <FormMessage kind="success">If that account exists, we sent a new confirmation link.</FormMessage>
          ) : (
            <Button type="button" variant="secondary" onClick={resend}>
              Send a new confirmation link
            </Button>
          ))}
        <Button type="submit" disabled={busy || !email || !password} className="w-full">
          {busy ? "Signing in…" : "Sign in"}
        </Button>
      </form>
      <div className="mt-6 space-y-2 text-sm text-ink-muted">
        <p>
          <Link href="/forgot-password" className="text-primary underline">Forgot your password?</Link>
        </p>
        <p>
          New here? <Link href="/register" className="text-primary underline">Create an account</Link>
        </p>
      </div>
    </div>
  );
}
