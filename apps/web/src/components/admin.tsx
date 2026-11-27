"use client";

import type { AdminRole, AdminUserDetail } from "@pdna/api-client";
import { type FormEvent, type ReactNode, useState } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { eventLabel, money } from "@/lib/admin";
import { errorMessage } from "@/lib/errors";
import { useAsync } from "@/lib/use-async";

const when = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : "—";

function Stat({ label, value, hint }: { label: string; value: ReactNode; hint?: string }) {
  return (
    <div className="rounded-card border border-line p-3">
      <dt className="text-sm text-ink-muted">{label}</dt>
      <dd className="mt-1 text-2xl font-semibold">{value}</dd>
      {hint && <dd className="text-xs text-ink-muted">{hint}</dd>}
    </div>
  );
}

function Loaded<T>({
  state,
  label,
  children,
}: {
  state: ReturnType<typeof useAsync<T>>;
  label: string;
  children: (data: T) => ReactNode;
}) {
  if (state.status === "loading") return <LoadingState label={`Loading ${label}`} />;
  if (state.status === "error")
    return (
      <ErrorState
        title={`We couldn't load ${label}`}
        message={errorMessage(state.error)}
        action={<Button onClick={state.reload}>Try again</Button>}
      />
    );
  return <>{children(state.data)}</>;
}

export function Overview({ canMetrics }: { canMetrics: boolean }) {
  const health = useAsync(() => api.adminHealth(), "admin-health");
  const metrics = useAsync(() => (canMetrics ? api.adminMetrics() : Promise.resolve(null)), `admin-metrics:${canMetrics}`);
  return (
    <div className="space-y-6">
      <Card as="section" aria-labelledby="health-heading">
        <h2 id="health-heading" className="text-xl font-semibold">
          System health
        </h2>
        <Loaded state={health} label="system health">
          {(h) => (
            <dl className="mt-3 grid gap-3 sm:grid-cols-3">
              <Stat label="Status" value={h.status === "ok" ? "OK" : "Degraded"} />
              <Stat label="Database" value={h.database ? "Reachable" : "Unreachable"} />
              <Stat label="Environment" value={h.environment} />
              <Stat label="AI coach" value={h.coach_enabled ? h.coach_provider : "Off"} />
              <Stat label="Email" value={h.email_provider} />
              <Stat
                label="Billing"
                value={h.billing_enforced ? "Enforced" : "Not enforced"}
                hint={`Stripe ${h.stripe_configured ? "configured" : "not configured"}, RevenueCat ${
                  h.revenuecat_configured ? "configured" : "not configured"
                }`}
              />
            </dl>
          )}
        </Loaded>
      </Card>
      {canMetrics && (
        <Loaded state={metrics} label="metrics">
          {(m) =>
            m && (
              <>
                <Card as="section" aria-labelledby="growth-heading">
                  <h2 id="growth-heading" className="text-xl font-semibold">
                    Accounts and activity
                  </h2>
                  <dl className="mt-3 grid gap-3 sm:grid-cols-3">
                    <Stat label="Accounts" value={m.users.total} hint={`${m.users.last_30_days} new in 30 days`} />
                    <Stat label="Confirmed email" value={m.verified_users} />
                    <Stat label="Disabled" value={m.disabled_users} />
                    <Stat
                      label="Completed assessments"
                      value={m.completed_assessments.total}
                      hint={`${m.completed_assessments.last_30_days} in 30 days`}
                    />
                    <Stat label="Reports created" value={m.reports_created.total} />
                    <Stat label="Shared cards" value={m.active_share_cards} />
                  </dl>
                  <h3 className="mt-4 font-semibold">Results by instrument</h3>
                  <ul className="mt-1 text-sm">
                    {Object.entries(m.assessments_by_instrument).map(([k, v]) => (
                      <li key={k}>
                        {k}: {v}
                      </li>
                    ))}
                  </ul>
                  <h3 className="mt-4 font-semibold">Accounts using each feature</h3>
                  <ul className="mt-1 text-sm">
                    {Object.entries(m.feature_users).map(([k, v]) => (
                      <li key={k}>
                        {k.replace(/_/g, " ")}: {v}
                      </li>
                    ))}
                  </ul>
                </Card>
                <Card as="section" aria-labelledby="revenue-heading">
                  <h2 id="revenue-heading" className="text-xl font-semibold">
                    Subscriptions and AI cost
                  </h2>
                  <dl className="mt-3 grid gap-3 sm:grid-cols-3">
                    <Stat label="Estimated monthly revenue" value={money(m.estimated_monthly_revenue_cents)} />
                    <Stat
                      label="Active subscriptions"
                      value={Object.values(m.active_subscriptions_by_plan).reduce((a, b) => a + b, 0)}
                      hint={Object.entries(m.active_subscriptions_by_provider)
                        .map(([k, v]) => `${k} ${v}`)
                        .join(", ")}
                    />
                    <Stat label="Coach turns (30 days)" value={m.coach_turns.last_30_days} />
                    <Stat
                      label="AI cost (30 days)"
                      value={m.coach_cost_30_days_usd == null ? "Not set" : `$${m.coach_cost_30_days_usd.toFixed(2)}`}
                      hint={`${m.coach_active_users_30_days} active coach users`}
                    />
                    <Stat
                      label="Tokens (30 days)"
                      value={(m.coach_tokens_30_days.input ?? 0) + (m.coach_tokens_30_days.output ?? 0)}
                      hint={`${m.coach_tokens_30_days.input ?? 0} in, ${m.coach_tokens_30_days.output ?? 0} out`}
                    />
                  </dl>
                  <p className="mt-3 text-sm text-ink-muted">{m.revenue_note}</p>
                  <p className="mt-1 text-sm text-ink-muted">{m.cost_note}</p>
                </Card>
              </>
            )
          }
        </Loaded>
      )}
    </div>
  );
}

export function Accounts({ permissions }: { permissions: string[] }) {
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState<string | null>(null);
  const list = useAsync(() => api.adminUsers(query), `admin-users:${query}`);

  function search(e: FormEvent) {
    e.preventDefault();
    setQuery(q);
    setSelected(null);
  }

  return (
    <div className="space-y-6">
      <form role="search" aria-label="Find an account" onSubmit={search} className="flex flex-wrap items-end gap-3">
        <div className="min-w-64 flex-1">
          <TextField id="admin-q" label="Email or account id" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <Button type="submit">Search</Button>
      </form>
      <Loaded state={list} label="accounts">
        {(d) =>
          d.users.length === 0 ? (
            <EmptyState title="No accounts found" message="Try part of the email address, or the full account id." />
          ) : (
            <ul className="space-y-2" aria-label="Accounts">
              {d.users.map((u) => (
                <li key={u.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(u.id)}
                    aria-pressed={selected === u.id}
                    className="block w-full rounded-card border border-line bg-surface p-3 text-left hover:bg-muted aria-pressed:border-primary"
                  >
                    <span className="block font-semibold">{u.email}</span>
                    <span className="block text-sm text-ink-muted">
                      Joined {when(u.created_at)} · {u.email_verified ? "confirmed" : "not confirmed"} · {u.status} ·{" "}
                      {u.plan_id}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )
        }
      </Loaded>
      {selected && <AccountDetail key={selected} id={selected} permissions={permissions} />}
    </div>
  );
}

const ROLE_OPTIONS: AdminRole[] = ["support", "analyst", "content", "security", "superadmin"];

function AccountDetail({ id, permissions }: { id: string; permissions: string[] }) {
  const loaded = useAsync(() => api.adminUser(id), `admin-user:${id}`);
  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [reason, setReason] = useState("");
  const [days, setDays] = useState("30");
  const [role, setRole] = useState<AdminRole>("support");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ kind: "error" | "success"; text: string } | null>(null);
  const can = (p: string) => permissions.includes(p);

  async function act(fn: () => Promise<AdminUserDetail>, done: string) {
    setBusy(true);
    setMessage(null);
    try {
      setUser(await fn());
      setMessage({ kind: "success", text: done });
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  }

  return (
    <Loaded state={loaded} label="the account">
      {(initial) => {
        const u = user ?? initial;
        const reasonOk = reason.trim().length >= 3;
        return (
          <Card as="section" aria-labelledby="account-heading">
            <h2 id="account-heading" className="text-xl font-semibold">
              {u.email}
            </h2>
            <p className="mt-1 text-sm text-ink-muted">
              Account metadata only. Journals, coaching conversations, answers and report contents are never shown here.
            </p>
            <dl className="mt-3 grid gap-3 sm:grid-cols-3">
              <Stat label="Status" value={u.status} />
              <Stat label="Plan" value={u.plan_id} />
              <Stat label="Joined" value={when(u.created_at)} />
              <Stat label="Completed assessments" value={u.completed_assessments} />
              <Stat label="Reports" value={u.reports} />
              <Stat label="Admin roles" value={u.admin_roles.length ? u.admin_roles.join(", ") : "None"} />
            </dl>
            {u.subscriptions.length > 0 && (
              <>
                <h3 className="mt-4 font-semibold">Subscriptions</h3>
                <ul className="mt-1 space-y-2 text-sm">
                  {u.subscriptions.map((s) => (
                    <li key={s.id} className="flex flex-wrap items-center gap-3">
                      <span>
                        {s.plan_id} via {s.provider}, {s.status}, ends {when(s.current_period_end)}
                      </span>
                      {s.provider === "manual" && s.status === "active" && can("subscriptions.manage") && (
                        <Button
                          variant="ghost"
                          disabled={busy}
                          onClick={() => act(() => api.adminRevokeGrant(u.id, s.id), "Complimentary access removed.")}
                        >
                          Remove complimentary access
                        </Button>
                      )}
                    </li>
                  ))}
                </ul>
              </>
            )}

            {(can("users.manage") || can("subscriptions.manage")) && (
              <div className="mt-6 space-y-4 border-t border-line pt-4">
                <TextField
                  id="admin-reason"
                  label="Reason (kept in the audit log)"
                  value={reason}
                  maxLength={500}
                  onChange={(e) => setReason(e.target.value)}
                />
                <div className="flex flex-wrap items-end gap-3">
                  {can("users.manage") && (
                    <Button
                      variant="secondary"
                      disabled={busy || !reasonOk}
                      onClick={() =>
                        act(
                          () => api.adminSetStatus(u.id, u.status === "active" ? "disabled" : "active", reason.trim()),
                          u.status === "active" ? "Account disabled and signed out." : "Account enabled.",
                        )
                      }
                    >
                      {u.status === "active" ? "Disable account" : "Enable account"}
                    </Button>
                  )}
                  {can("subscriptions.manage") && (
                    <>
                      <div className="w-32">
                        <TextField
                          id="admin-days"
                          label="Days"
                          type="number"
                          min={1}
                          max={366}
                          value={days}
                          onChange={(e) => setDays(e.target.value)}
                        />
                      </div>
                      <Button
                        variant="secondary"
                        disabled={busy || !reasonOk || !(Number(days) >= 1 && Number(days) <= 366)}
                        onClick={() =>
                          act(
                            () => api.adminGrant(u.id, "premium-monthly", Number(days), reason.trim()),
                            "Complimentary Premium granted.",
                          )
                        }
                      >
                        Grant complimentary Premium
                      </Button>
                    </>
                  )}
                </div>
              </div>
            )}

            {can("roles.manage") && (
              <div className="mt-6 space-y-3 border-t border-line pt-4">
                <h3 className="font-semibold">Admin roles</h3>
                <div className="flex flex-wrap items-end gap-3">
                  <div>
                    <label htmlFor="admin-role" className="block font-medium">
                      Role
                    </label>
                    <select
                      id="admin-role"
                      value={role}
                      onChange={(e) => setRole(e.target.value as AdminRole)}
                      className="mt-1 block min-h-12 rounded-xl border border-line bg-surface px-3 text-ink"
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                  </div>
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => act(() => api.adminAddRole(u.id, role), `Role ${role} granted.`)}
                  >
                    Grant role
                  </Button>
                  {u.admin_roles.map((r) => (
                    <Button
                      key={r}
                      variant="ghost"
                      disabled={busy}
                      onClick={() => act(() => api.adminRemoveRole(u.id, r), `Role ${r} removed.`)}
                    >
                      Remove {r}
                    </Button>
                  ))}
                </div>
              </div>
            )}
            {message && <FormMessage kind={message.kind}>{message.text}</FormMessage>}
          </Card>
        );
      }}
    </Loaded>
  );
}

export function ContentPanel() {
  const data = useAsync(() => api.adminContent(), "admin-content");
  return (
    <Loaded state={data} label="content">
      {(c) => (
        <div className="space-y-6">
          <Card as="section" aria-labelledby="versions-heading">
            <h2 id="versions-heading" className="text-xl font-semibold">
              Versions
            </h2>
            <dl className="mt-3 grid gap-3 sm:grid-cols-4">
              <Stat label="Scoring engine" value={c.engine_version} />
              <Stat label="Reports" value={c.report_version} />
              <Stat label="Coach prompt" value={c.coach_prompt} />
              <Stat label="Plans" value={c.plans_version} />
            </dl>
            <p className="mt-3 text-sm text-ink-muted">{c.note}</p>
          </Card>
          <Card as="section" aria-labelledby="instruments-heading">
            <h2 id="instruments-heading" className="text-xl font-semibold">
              Instruments
            </h2>
            <ul className="mt-3 space-y-3">
              {c.instruments.map((i) => (
                <li key={`${i.id}@${i.version}`}>
                  <p className="font-semibold">
                    {i.name} ({i.id} {i.version})
                  </p>
                  <p className="text-sm text-ink-muted">
                    {i.family}, {i.tier}, {i.items} items, {i.status}, licence {i.license}
                  </p>
                  <p className="break-all text-xs text-ink-muted">SHA-256 {i.sha256}</p>
                </li>
              ))}
            </ul>
          </Card>
          <Card as="section" aria-labelledby="files-heading">
            <h2 id="files-heading" className="text-xl font-semibold">
              Content files
            </h2>
            <ul className="mt-3 space-y-2 text-sm">
              {c.files.map((f) => (
                <li key={f.name}>
                  <span className="font-medium">{f.name}</span> (version {f.version})
                  <span className="block break-all text-xs text-ink-muted">SHA-256 {f.sha256}</span>
                </li>
              ))}
            </ul>
          </Card>
        </div>
      )}
    </Loaded>
  );
}

export function AuditPanel() {
  const [filter, setFilter] = useState("");
  const [applied, setApplied] = useState("");
  const first = useAsync(() => api.adminAudit(null, applied || undefined), `admin-audit:${applied}`);
  const [extra, setExtra] = useState<{ key: string; items: Awaited<ReturnType<typeof api.adminAudit>>["items"]; next: string | null }>({
    key: "",
    items: [],
    next: null,
  });
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="space-y-4">
      <form
        role="search"
        aria-label="Filter the audit log"
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setApplied(filter.trim());
        }}
      >
        <div className="min-w-64 flex-1">
          <TextField
            id="audit-filter"
            label="Event type starts with"
            hint="For example: admin. or auth."
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
        </div>
        <Button type="submit">Filter</Button>
      </form>
      <Loaded state={first} label="the audit log">
        {(d) => {
          const more = extra.key === applied ? extra : { key: applied, items: [], next: d.next_before ?? null };
          const items = [...d.items, ...more.items];
          const next = extra.key === applied ? extra.next : (d.next_before ?? null);
          return items.length === 0 ? (
            <EmptyState title="No events" message="Nothing matches this filter." />
          ) : (
            <>
              <ul className="space-y-2" aria-label="Audit events">
                {items.map((e) => (
                  <li key={e.id} className="rounded-card border border-line p-3 text-sm">
                    <span className="font-semibold">{eventLabel(e.event_type)}</span>{" "}
                    <span className="text-ink-muted">· {when(e.created_at)}</span>
                    <span className="block break-all text-xs text-ink-muted">
                      {e.subject_type} {e.subject_id} {Object.keys(e.details).length ? JSON.stringify(e.details) : ""}
                    </span>
                  </li>
                ))}
              </ul>
              {next && (
                <Button
                  variant="secondary"
                  onClick={async () => {
                    setError(null);
                    try {
                      const page = await api.adminAudit(next, applied || undefined);
                      setExtra({ key: applied, items: [...more.items, ...page.items], next: page.next_before ?? null });
                    } catch (err) {
                      setError(errorMessage(err));
                    }
                  }}
                >
                  Show older events
                </Button>
              )}
              {error && <FormMessage kind="error">{error}</FormMessage>}
            </>
          );
        }}
      </Loaded>
    </div>
  );
}
