"use client";

import type { Org, OrgMember, OrgRole, Schemas } from "@pdna/api-client";
import { useRouter } from "next/navigation";
import { type FormEvent, type ReactNode, useState } from "react";
import { FormMessage, TextField } from "@/components/form";
import { Button, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage } from "@/lib/errors";
import { analyticsStatus, bandShares, orgInviteLink, ROLE_LABEL } from "@/lib/orgs";
import { useAsync } from "@/lib/use-async";

const date = (iso: string) => new Date(iso).toLocaleDateString(undefined, { dateStyle: "medium" });

function Panel({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <Card as="section" aria-labelledby={id}>
      <h2 id={id} className="text-xl font-semibold">
        {title}
      </h2>
      {children}
    </Card>
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

export function Analytics({ orgId }: { orgId: string }) {
  const data = useAsync(() => api.orgAnalytics(orgId), `analytics:${orgId}`);
  return (
    <Panel id="analytics-heading" title="Group statistics">
      <Loaded state={data} label="group statistics">
        {(a) => {
          const status = analyticsStatus(a);
          return (
            <div className="mt-3 space-y-4">
              <p className="text-sm text-ink-muted">{a.note}</p>
              <dl className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-card border border-line p-3">
                  <dt className="text-sm text-ink-muted">Members</dt>
                  <dd className="mt-1 text-2xl font-semibold">
                    {a.members} <span className="text-base font-normal text-ink-muted">of {a.seat_limit} seats</span>
                  </dd>
                </div>
                <div className="rounded-card border border-line p-3">
                  <dt className="text-sm text-ink-muted">Sharing with results</dt>
                  <dd className="mt-1 text-2xl font-semibold">{a.consenting_members ?? `Fewer than ${a.min_group}`}</dd>
                </div>
              </dl>
              {status && <p role="status">{status}</p>}
              {a.traits.some((t) => t.bands) && (
                <table className="w-full text-left text-sm">
                  <caption className="sr-only">Share of sharing members in each band, by trait</caption>
                  <thead>
                    <tr className="border-b border-line">
                      <th scope="col" className="py-2">
                        Trait
                      </th>
                      <th scope="col">Lower</th>
                      <th scope="col">Middle</th>
                      <th scope="col">Higher</th>
                    </tr>
                  </thead>
                  <tbody>
                    {a.traits.map((t) => {
                      const s = t.bands ? bandShares(t.bands) : null;
                      return (
                        <tr key={t.trait} className="border-b border-line">
                          <th scope="row" className="py-2 font-medium">
                            {t.name}
                          </th>
                          {s ? (
                            <>
                              <td>{s.lower}%</td>
                              <td>{s.middle}%</td>
                              <td>{s.higher}%</td>
                            </>
                          ) : (
                            <td colSpan={3} className="text-ink-muted">
                              Hidden to protect individuals
                            </td>
                          )}
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
              {a.programs.length > 0 && (
                <div>
                  <h3 className="font-semibold">Programme participation</h3>
                  <ul className="mt-2 space-y-1">
                    {a.programs.map((p) => (
                      <li key={p.id}>
                        {p.title}: {p.participants ?? `fewer than ${a.min_cell}`} joined
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        }}
      </Loaded>
    </Panel>
  );
}

export function Invitations({ orgId, role, onChange }: { orgId: string; role: OrgRole; onChange: () => void }) {
  const list = useAsync(() => api.orgInvitations(orgId), `invitations:${orgId}`);
  const [inviteRole, setInviteRole] = useState<"member" | "admin">("member");
  const [uses, setUses] = useState("10");
  const [link, setLink] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const res = await api.createOrgInvitation(orgId, {
        role: inviteRole,
        max_uses: Number(uses) || 1,
        days: 14,
      });
      setLink(orgInviteLink(window.location.origin, res.token));
      list.reload();
      onChange();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function cancel(id: string) {
    setError(null);
    try {
      await api.cancelOrgInvitation(orgId, id);
      list.reload();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <Panel id="invite-heading" title="Invite people">
      <form onSubmit={create} className="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="invite-role" className="block font-medium">
            Join as
          </label>
          <select
            id="invite-role"
            value={inviteRole}
            onChange={(e) => setInviteRole(e.target.value as "member" | "admin")}
            className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
          >
            <option value="member">Member</option>
            {role === "owner" && <option value="admin">Administrator</option>}
          </select>
        </div>
        <TextField
          id="invite-uses"
          label="How many people can use it"
          type="number"
          min={1}
          max={500}
          value={uses}
          onChange={(e) => setUses(e.target.value)}
        />
        <div className="sm:col-span-2">
          <Button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create join link"}
          </Button>
        </div>
      </form>
      {error && <FormMessage kind="error">{error}</FormMessage>}
      {link && (
        <div className="mt-6 space-y-2 rounded-card border border-line p-4">
          <label htmlFor="org-invite-link" className="font-medium">
            Join link
          </label>
          <p className="text-sm text-ink-muted">
            Share it with the people you want to invite. It expires in 14 days, and each person who joins takes a seat.
            We show it only now.
          </p>
          <input
            id="org-invite-link"
            readOnly
            value={link}
            onFocus={(e) => e.target.select()}
            className="block w-full rounded-card border border-line bg-surface p-3 text-sm text-ink"
          />
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="secondary" onClick={copy}>
              Copy link
            </Button>
            <span role="status" className="text-sm text-ink-muted">
              {copied ? "Copied." : ""}
            </span>
          </div>
        </div>
      )}
      <Loaded state={list} label="open links">
        {(d) =>
          d.invitations.length === 0 ? null : (
            <ul className="mt-6 space-y-2">
              {d.invitations.map((i) => (
                <li
                  key={i.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-line p-3"
                >
                  <span>
                    {ROLE_LABEL[i.role]} link · {i.uses} of {i.max_uses} used · expires {date(i.expires_at)}
                  </span>
                  <Button
                    variant="secondary"
                    onClick={() => cancel(i.id)}
                    aria-label={`Cancel ${ROLE_LABEL[i.role].toLowerCase()} link`}
                  >
                    Cancel
                  </Button>
                </li>
              ))}
            </ul>
          )
        }
      </Loaded>
    </Panel>
  );
}

export function Members({ orgId, role, onChange }: { orgId: string; role: OrgRole; onChange: () => void }) {
  const list = useAsync(() => api.orgMembers(orgId), `members:${orgId}`);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setError(null);
    try {
      await fn();
      list.reload();
      onChange();
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <Panel id="members-heading" title="Members">
      <p className="mt-2 text-sm text-ink-muted">
        You see names, emails and roles. Results, reports and whether someone shares in group statistics are never
        shown.
      </p>
      {error && <FormMessage kind="error">{error}</FormMessage>}
      <Loaded state={list} label="members">
        {(d) => (
          <ul className="mt-4 divide-y divide-line">
            {d.members.map((m: OrgMember) => (
              <li key={m.id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <span>
                  <span className="block font-medium">{m.display_name || m.email}</span>
                  <span className="text-sm text-ink-muted">
                    {m.display_name ? `${m.email} · ` : ""}joined {date(m.joined_at)}
                  </span>
                </span>
                <span className="flex flex-wrap items-center gap-2">
                  {role === "owner" ? (
                    <select
                      aria-label={`Role for ${m.display_name || m.email}`}
                      value={m.role}
                      onChange={(e) => run(() => api.setOrgRole(orgId, m.id, e.target.value as OrgRole))}
                      className="rounded-card border border-line bg-surface p-2 text-ink"
                    >
                      <option value="member">Member</option>
                      <option value="admin">Administrator</option>
                      <option value="owner">Owner</option>
                    </select>
                  ) : (
                    <span className="text-sm">{ROLE_LABEL[m.role]}</span>
                  )}
                  {(role === "owner" || m.role === "member") && (
                    <Button
                      variant="secondary"
                      onClick={() => run(() => api.removeOrgMember(orgId, m.id))}
                      aria-label={`Remove ${m.display_name || m.email}`}
                    >
                      Remove
                    </Button>
                  )}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Loaded>
    </Panel>
  );
}

export function NewProgram({ orgId, onCreated }: { orgId: string; onCreated: () => void }) {
  const catalog = useAsync(() => api.orgCatalog(), "org-catalog");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [growth, setGrowth] = useState("");
  const [modules, setModules] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const learning = modules.map((ref) => {
      const [track, module] = ref.split(":");
      return { track, module } as Schemas["LearningRef"];
    });
    try {
      await api.createOrgProgram(orgId, {
        title,
        description,
        growth_program_id: growth || null,
        learning,
      });
      setTitle("");
      setDescription("");
      setGrowth("");
      setModules([]);
      onCreated();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  const toggle = (ref: string) =>
    setModules((m) => (m.includes(ref) ? m.filter((x) => x !== ref) : m.length < 6 ? [...m, ref] : m));

  return (
    <Panel id="new-program-heading" title="Create a programme">
      <Loaded state={catalog} label="programme options">
        {(c) => (
          <form onSubmit={create} className="mt-4 space-y-4">
            <TextField
              id="program-title"
              label="Title"
              required
              minLength={2}
              maxLength={120}
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
            <div>
              <label htmlFor="program-description" className="block font-medium">
                Description (optional)
              </label>
              <textarea
                id="program-description"
                maxLength={1000}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
              />
            </div>
            <div>
              <label htmlFor="program-growth" className="block font-medium">
                Growth programme
              </label>
              <select
                id="program-growth"
                value={growth}
                onChange={(e) => setGrowth(e.target.value)}
                className="mt-1 block w-full rounded-card border border-line bg-surface p-3 text-ink"
              >
                <option value="">None</option>
                {c.growth_programs.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.title} ({g.detail})
                  </option>
                ))}
              </select>
            </div>
            {(
              [
                ["leadership", "Leadership modules", c.leadership],
                ["emotional-awareness", "Emotional awareness modules", c.emotional_awareness],
              ] as const
            ).map(([track, label, items]) => (
              <fieldset key={track}>
                <legend className="font-medium">{label}</legend>
                <div className="mt-2 grid gap-2 sm:grid-cols-2">
                  {items.map((m) => {
                    const ref = `${track}:${m.id}`;
                    return (
                      <label key={ref} className="flex items-start gap-2">
                        <input
                          type="checkbox"
                          className="mt-1 h-4 w-4 accent-[var(--pdna-primary)]"
                          checked={modules.includes(ref)}
                          onChange={() => toggle(ref)}
                        />
                        <span>{m.title}</span>
                      </label>
                    );
                  })}
                </div>
              </fieldset>
            ))}
            {error && <FormMessage kind="error">{error}</FormMessage>}
            <Button type="submit" disabled={busy}>
              {busy ? "Creating…" : "Create programme"}
            </Button>
          </form>
        )}
      </Loaded>
    </Panel>
  );
}

export function Settings({ org, onChange }: { org: Org; onChange: () => void }) {
  const router = useRouter();
  const [name, setName] = useState(org.name);
  const [confirming, setConfirming] = useState(false);
  const [message, setMessage] = useState<{
    kind: "error" | "success";
    text: string;
  } | null>(null);

  async function rename(e: FormEvent) {
    e.preventDefault();
    setMessage(null);
    try {
      await api.renameOrg(org.id, name);
      setMessage({ kind: "success", text: "Saved." });
      onChange();
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err) });
    }
  }

  async function remove() {
    try {
      await api.deleteOrg(org.id);
      router.push("/orgs");
    } catch (err) {
      setMessage({ kind: "error", text: errorMessage(err) });
    }
  }

  return (
    <Panel id="settings-heading" title="Settings">
      <form onSubmit={rename} className="mt-4 space-y-3">
        <TextField
          id="org-rename"
          label="Name"
          required
          minLength={2}
          maxLength={120}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <Button type="submit" variant="secondary">
          Save name
        </Button>
      </form>
      {message && <FormMessage kind={message.kind}>{message.text}</FormMessage>}
      {org.role === "owner" && (
        <div className="mt-6 space-y-2">
          <p className="text-sm text-ink-muted">
            Deleting removes the organisation, its programmes and join links. Members keep their own accounts and
            results.
          </p>
          {confirming ? (
            <div className="flex flex-wrap gap-3">
              <Button onClick={remove}>Yes, delete {org.name}</Button>
              <Button variant="secondary" onClick={() => setConfirming(false)}>
                Keep it
              </Button>
            </div>
          ) : (
            <Button variant="secondary" onClick={() => setConfirming(true)}>
              Delete organisation
            </Button>
          )}
        </div>
      )}
    </Panel>
  );
}
