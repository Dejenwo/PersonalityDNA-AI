"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { BillingCard } from "@/components/billing-card";
import { FormMessage, TextField } from "@/components/form";
import { Button, Card, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { errorMessage } from "@/lib/errors";

export default function AccountPage() {
  const { state, signOut, setUser, forget } = useAuth();
  const router = useRouter();
  const [name, setName] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [password, setPassword] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const leaving = useRef(false);

  useEffect(() => {
    if (state.status === "signed-out" && !leaving.current) router.replace("/login");
  }, [state.status, router]);

  if (state.status !== "signed-in") return <LoadingState label="Loading your account" />;
  const user = state.user;
  const displayName = name ?? user.display_name ?? "";

  async function saveProfile(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(null);
    try {
      setUser(await api.updateMe({ display_name: displayName }));
      setSaved("Saved.");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function download() {
    setExporting(true);
    setError(null);
    try {
      const data = await api.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `personalitydna-export-${new Date().toISOString().slice(0, 10)}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setExporting(false);
    }
  }

  async function remove(e: FormEvent) {
    e.preventDefault();
    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteAccount(password);
      leaving.current = true;
      forget();
      router.replace("/?deleted=1");
    } catch (err) {
      setDeleteError(errorMessage(err));
      setDeleting(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-3xl font-bold">Your account</h1>

      <Card>
        <h2 className="text-xl font-semibold">Profile</h2>
        <p className="mt-1 text-ink-muted">{user.email}</p>
        <form onSubmit={saveProfile} className="mt-4 space-y-3">
          <TextField id="display-name" label="Name" value={displayName} maxLength={80}
            onChange={(e) => setName(e.target.value)} />
          {saved && <FormMessage kind="success">{saved}</FormMessage>}
          {error && <FormMessage kind="error">{error}</FormMessage>}
          <Button type="submit" variant="secondary">Save</Button>
        </form>
      </Card>

      <BillingCard />

      <Card>
        <h2 className="text-xl font-semibold">Your data</h2>
        <p className="mt-1 text-ink-muted">
          Download everything we store about you, including your answers and results, as a JSON file.
        </p>
        <Button variant="secondary" className="mt-4" onClick={download} disabled={exporting}>
          {exporting ? "Preparing…" : "Download my data"}
        </Button>
      </Card>

      <Card>
        <h2 className="text-xl font-semibold">Sign out</h2>
        <p className="mt-1 text-ink-muted">Ends your session on this device.</p>
        <Button variant="secondary" className="mt-4" onClick={async () => {
            leaving.current = true;
            await signOut();
            router.push("/");
          }}>
          Sign out
        </Button>
      </Card>

      <Card className="border-danger">
        <h2 className="text-xl font-semibold">Delete account</h2>
        <p className="mt-1 text-ink-muted">
          Permanently deletes your account and every assessment, answer and result linked to it. This can’t be undone.
        </p>
        {!confirmDelete ? (
          <Button variant="secondary" className="mt-4" onClick={() => setConfirmDelete(true)}>
            Delete my account…
          </Button>
        ) : (
          <form onSubmit={remove} className="mt-4 space-y-3">
            <TextField id="delete-password" label="Enter your password to confirm" type="password"
              autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
            {deleteError && <FormMessage kind="error">{deleteError}</FormMessage>}
            <div className="flex flex-wrap gap-3">
              <Button type="submit" disabled={!password || deleting}
                className="!bg-[var(--pdna-danger)] !text-[var(--pdna-primary-text)]">
                {deleting ? "Deleting…" : "Permanently delete"}
              </Button>
              <Button type="button" variant="secondary" onClick={() => setConfirmDelete(false)}>Cancel</Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  );
}
