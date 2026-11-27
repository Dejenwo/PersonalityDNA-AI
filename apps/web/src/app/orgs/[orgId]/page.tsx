"use client";

import type { Org, OrgProgram } from "@pdna/api-client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { FormMessage } from "@/components/form";
import { Analytics, Invitations, Members, NewProgram, Settings } from "@/components/org-panels";
import { Button, ButtonLink, Card, EmptyState, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { errorMessage, isNotFound } from "@/lib/errors";
import { canManage, licenceLabel, seatsLabel } from "@/lib/orgs";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function OrgPage() {
  const { orgId } = useParams<{ orgId: string }>();
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const org = useAsync(() => (signedIn ? api.org(orgId) : Promise.resolve(null)), `${orgId}:${signedIn}`);

  if (!signedIn || org.status === "loading" || (org.status === "success" && !org.data))
    return <LoadingState label="Loading the organisation" />;
  if (org.status === "error")
    return (
      <ErrorState level={1}
        title={isNotFound(org.error) ? "Organisation not available" : "We couldn't load this organisation"}
        message={isNotFound(org.error) ? "You may have left it, or it may have been deleted." : errorMessage(org.error)}
        action={<ButtonLink href="/orgs">Organisations</ButtonLink>}
      />
    );
  return <OrgView initial={org.data!} />;
}

function OrgView({ initial }: { initial: Org }) {
  // Updated in place after changes, so panels (and a freshly created join link) stay mounted.
  const [org, setOrg] = useState(initial);
  const reload = () => {
    api.org(org.id).then(setOrg, () => undefined);
  };
  const manager = canManage(org.role);
  const programs = useAsync(() => api.orgPrograms(org.id), `programs:${org.id}`);
  return (
    <div className="mx-auto max-w-3xl space-y-8">
      <header>
        <p className="text-sm text-ink-muted">
          <Link href="/orgs" className="underline">
            Organisations
          </Link>
        </p>
        <h1 className="mt-1 text-3xl font-bold">{org.name}</h1>
        <p className="mt-2 text-ink-muted">
          You&apos;re {org.role === "member" ? "a member" : org.role === "admin" ? "an administrator" : "the owner"}.{" "}
          {seatsLabel(org.licence)}. {licenceLabel(org.licence)}.
        </p>
      </header>

      <section aria-labelledby="programs-heading" className="space-y-4">
        <h2 id="programs-heading" className="text-xl font-semibold">
          Development programmes
        </h2>
        <p className="text-sm text-ink-muted">
          Joining a programme is up to you. The organisation only sees how many people joined, and only once there are
          at least 3.
        </p>
        {programs.status === "loading" && <LoadingState label="Loading programmes" />}
        {programs.status === "error" && (
          <ErrorState
            title="We couldn't load programmes"
            message={errorMessage(programs.error)}
            action={<Button onClick={programs.reload}>Try again</Button>}
          />
        )}
        {programs.status === "success" &&
          (programs.data.programs.length === 0 ? (
            <EmptyState
              title="No programmes yet"
              message={
                manager ? "Create one below from the growth programmes and learning modules." : "Check back later."
              }
            />
          ) : (
            <ul className="space-y-3">
              {programs.data.programs.map((p) => (
                <ProgramCard key={p.id} orgId={org.id} program={p} manager={manager} onChange={programs.reload} />
              ))}
            </ul>
          ))}
        {manager && <NewProgram orgId={org.id} onCreated={programs.reload} />}
      </section>

      <Sharing org={org} onChange={reload} />

      {manager && (
        <>
          <Analytics orgId={org.id} />
          <Invitations orgId={org.id} role={org.role} onChange={reload} />
          <Members orgId={org.id} role={org.role} onChange={reload} />
          <Settings org={org} onChange={reload} />
        </>
      )}

      <Leave org={org} />
    </div>
  );
}

function ProgramCard({
  orgId,
  program,
  manager,
  onChange,
}: {
  orgId: string;
  program: OrgProgram;
  manager: boolean;
  onChange: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(fn: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      onChange();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li>
      <Card as="article" aria-labelledby={`program-${program.id}`}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 id={`program-${program.id}`} className="text-lg font-semibold">
              {program.title}
            </h3>
            {program.description && <p className="mt-1 text-ink-muted">{program.description}</p>}
          </div>
          {program.joined && <span className="rounded-full bg-muted px-3 py-1 text-sm">Joined</span>}
        </div>
        <ul className="mt-3 list-disc space-y-1 pl-5">
          {program.items.map((i) => (
            <li key={i.href}>
              <Link href={i.href} className="text-primary underline">
                {i.title}
              </Link>{" "}
              <span className="text-sm text-ink-muted">
                {i.kind === "growth" ? "Growth programme" : "Learning module"}
              </span>
            </li>
          ))}
        </ul>
        <div className="mt-4 flex flex-wrap gap-3">
          <Button
            variant={program.joined ? "secondary" : "primary"}
            disabled={busy}
            onClick={() => run(() => api.setOrgProgramJoined(orgId, program.id, !program.joined))}
          >
            {program.joined ? "Leave programme" : "Join programme"}
          </Button>
          {manager && (
            <Button
              variant="secondary"
              disabled={busy}
              onClick={() => run(() => api.deleteOrgProgram(orgId, program.id))}
              aria-label={`Delete programme ${program.title}`}
            >
              Delete
            </Button>
          )}
        </div>
        {error && <FormMessage kind="error">{error}</FormMessage>}
      </Card>
    </li>
  );
}

function Sharing({ org, onChange }: { org: Org; onChange: () => void }) {
  // Shown straight away; put back if saving fails.
  const [checked, setChecked] = useState(org.share_aggregates);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function toggle(share: boolean) {
    setChecked(share);
    setBusy(true);
    setError(null);
    try {
      await api.setOrgSharing(org.id, share);
      onChange();
    } catch (err) {
      setChecked(!share);
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card as="section" aria-labelledby="sharing-heading">
      <h2 id="sharing-heading" className="text-xl font-semibold">
        Anonymous group statistics
      </h2>
      <p className="mt-2 text-ink-muted">
        You can let {org.name} count whether each of your Big Five traits from your latest result is lower, middle or
        higher in group totals. Totals only appear when at least 10 people share and every band has at least 3 people.
        Nobody, including administrators, can see your own result or whether you chose to share.
      </p>
      <label className="mt-4 flex gap-3">
        <input
          type="checkbox"
          className="mt-1 h-5 w-5 accent-[var(--pdna-primary)]"
          checked={checked}
          disabled={busy}
          onChange={(e) => toggle(e.target.checked)}
        />
        <span>Include my latest Big Five bands in {org.name}&apos;s anonymous group statistics</span>
      </label>
      {error && <FormMessage kind="error">{error}</FormMessage>}
    </Card>
  );
}

function Leave({ org }: { org: Org }) {
  const router = useRouter();
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function leave() {
    setError(null);
    try {
      await api.leaveOrg(org.id);
      router.push("/orgs");
    } catch (err) {
      setError(errorMessage(err));
    }
  }

  return (
    <section aria-labelledby="leave-heading" className="space-y-3">
      <h2 id="leave-heading" className="text-xl font-semibold">
        Leave {org.name}
      </h2>
      <p className="text-ink-muted">
        You can leave at any time. Your programme participation here is removed; your own results, reports and progress
        stay in your account.{" "}
        {org.role === "owner" ? "If you are the only owner, make someone else an owner first." : ""}
      </p>
      {confirming ? (
        <div className="flex flex-wrap gap-3">
          <Button onClick={leave}>Yes, leave</Button>
          <Button variant="secondary" onClick={() => setConfirming(false)}>
            Stay
          </Button>
        </div>
      ) : (
        <Button variant="secondary" onClick={() => setConfirming(true)}>
          Leave organisation
        </Button>
      )}
      {error && <FormMessage kind="error">{error}</FormMessage>}
    </section>
  );
}
