"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.requestPasswordReset(email);
      setSent(true);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-3xl font-bold">Reset your password</h1>
      {sent ? (
        <div className="mt-4">
          <FormMessage kind="success">
            If an account exists for {email}, we sent a link to reset the password. It expires in 60 minutes.
          </FormMessage>
          <p className="mt-4 text-sm"><Link href="/login" className="text-primary underline">Back to sign in</Link></p>
        </div>
      ) : (
        <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
          <TextField id="email" label="Email" type="email" autoComplete="email" required value={email}
            onChange={(e) => setEmail(e.target.value)} />
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <Button type="submit" disabled={busy || !email} className="w-full">
            {busy ? "Sending…" : "Send reset link"}
          </Button>
        </form>
      )}
    </div>
  );
}
