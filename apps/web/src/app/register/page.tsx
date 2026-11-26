"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button, Card } from "@/components/ui";
import { api, PRIVACY_POLICY_VERSION } from "@/lib/api";
import { errorMessage } from "@/lib/errors";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [adult, setAdult] = useState(false);
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.register({
        email,
        password,
        display_name: name.trim() || null,
        accepted_terms: terms,
        age_confirmed_18_plus: adult,
        policy_version: PRIVACY_POLICY_VERSION,
      });
      setSentTo(email);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  if (sentTo) {
    return (
      <Card className="mx-auto max-w-md">
        <h1 className="text-2xl font-bold">Check your email</h1>
        <p className="mt-2 text-ink-muted">
          We sent a confirmation link to <strong className="text-ink">{sentTo}</strong>. Open it to finish creating
          your account. The link expires in 24 hours.
        </p>
        <p className="mt-4 text-sm text-ink-muted">
          Already confirmed? <Link href="/login" className="text-primary underline">Sign in</Link>
        </p>
      </Card>
    );
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="text-3xl font-bold">Create your account</h1>
      <p className="mt-2 text-ink-muted">
        Keep your results across devices and come back to them anytime. Assessments you took on this device are added
        to your account when you sign in.
      </p>
      <form onSubmit={submit} className="mt-6 space-y-4" noValidate>
        <TextField id="name" label="Name (optional)" autoComplete="nickname" value={name} maxLength={80}
          onChange={(e) => setName(e.target.value)} />
        <TextField id="email" label="Email" type="email" autoComplete="email" required value={email}
          onChange={(e) => setEmail(e.target.value)} />
        <TextField id="password" label="Password" type="password" autoComplete="new-password" required
          hint="At least 10 characters. A short phrase works well." value={password} minLength={10}
          onChange={(e) => setPassword(e.target.value)} />
        <label className="flex items-start gap-3">
          <input type="checkbox" className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]" checked={adult}
            onChange={(e) => setAdult(e.target.checked)} />
          <span>I confirm I am 18 or older.</span>
        </label>
        <label className="flex items-start gap-3">
          <input type="checkbox" className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]" checked={terms}
            onChange={(e) => setTerms(e.target.checked)} />
          <span>
            I agree to the{" "}
            <Link href="/privacy" target="_blank" className="text-primary underline">privacy notice</Link>.
          </span>
        </label>
        {error && <FormMessage kind="error">{error}</FormMessage>}
        <Button type="submit" disabled={busy || !email || !password || !adult || !terms} className="w-full">
          {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-ink-muted">
        Have an account? <Link href="/login" className="text-primary underline">Sign in</Link>
      </p>
    </div>
  );
}
