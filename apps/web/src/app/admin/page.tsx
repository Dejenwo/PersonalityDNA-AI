"use client";

import { useState } from "react";
import { AuditPanel, Accounts, ContentPanel, Overview } from "@/components/admin";
import { ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { type AdminTab, TAB_LABEL, tabsFor } from "@/lib/admin";
import { isNotFound } from "@/lib/errors";
import { errorMessage } from "@/lib/errors";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function AdminPage() {
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const me = useAsync(() => (signedIn ? api.adminMe() : Promise.resolve(null)), `admin-me:${signedIn}`);
  const [tab, setTab] = useState<AdminTab | null>(null);

  if (!signedIn || me.status === "loading" || (me.status === "success" && !me.data))
    return <LoadingState label="Loading" />;
  if (me.status === "error")
    return isNotFound(me.error) ? (
      <ErrorState title="Page not found" message="This page doesn't exist or you don't have access to it." />
    ) : (
      <ErrorState title="We couldn't load this page" message={errorMessage(me.error)} />
    );

  const permissions = me.data!.permissions;
  const tabs = tabsFor(permissions);
  const current = tab && tabs.includes(tab) ? tab : tabs[0];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold">Administration</h1>
        <p className="mt-2 text-ink-muted">Your roles: {me.data!.roles.join(", ")}. Every change here is recorded in the audit log.</p>
      </header>
      <nav aria-label="Admin sections">
        <ul className="flex flex-wrap gap-2">
          {tabs.map((t) => (
            <li key={t}>
              <button
                type="button"
                aria-current={t === current ? "page" : undefined}
                onClick={() => setTab(t)}
                className="rounded-full border border-line px-4 py-2 aria-[current=page]:border-primary aria-[current=page]:bg-muted"
              >
                {TAB_LABEL[t]}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      {current === "overview" && <Overview canMetrics={permissions.includes("metrics.read")} />}
      {current === "users" && <Accounts permissions={permissions} />}
      {current === "content" && <ContentPanel />}
      {current === "audit" && <AuditPanel />}
    </div>
  );
}
