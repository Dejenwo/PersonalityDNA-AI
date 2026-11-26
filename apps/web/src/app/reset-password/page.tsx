"use client";

import { useEffect, useState, type FormEvent } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button, ButtonLink, Card } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { takeFragmentToken } from "@/lib/token";

export default function ResetPasswordPage() {
  const [token, setToken] = useState<string | null | undefined>(undefined);
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => setToken(takeFragmentToken("token")))();
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!token) return;
    setBusy(true);
    setError(null);
    try {
      await api.confirmPasswordReset(token, password);
      setDone(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <Card className="mx-auto max-w-md">
        <h1 className="text-2xl font-bold">Password updated</h1>
        <p className="mt-2 text-ink-muted">You’ve been signed out everywhere. Sign in with your new password.</p>
        <ButtonLink href="/login" className="mt-4">Sign in</ButtonLink>
      </Card>
    );
  }
  if (token === null) {
    return (
      <Card className="mx-auto max-w-md">
        <h1 className="text-2xl font-bold">This link is incomplete</h1>
        <p className="mt-2 text-ink-muted">Open the link from your email again, or request a new one.</p>
        <ButtonLink href="/forgot-password" className="mt-4">Request a new link</ButtonLink>
      </Card>
    );
  }
  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-3xl font-bold">Choose a new password</h1>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <TextField id="password" label="New password" type="password" autoComplete="new-password" required
          hint="At least 10 characters." value={password} onChange={(e) => setPassword(e.target.value)} />
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Button type="submit" disabled={busy || !password || !token} className="w-full">
          {busy ? "Saving…" : "Save new password"}
        </Button>
      </form>
    </div>
  );
}
