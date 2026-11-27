"use client";

import type { Report } from "@pdna/api-client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { type ReactNode, useState } from "react";
import { FormMessage } from "@/components/form";
import { Button, ButtonLink, Card, ErrorState, LoadingState } from "@/components/ui";
import { api } from "@/lib/api";
import { downloadBlob } from "@/lib/download";
import { errorMessage, isNotFound } from "@/lib/errors";
import { allLimitations, allReferences, reportFilename, traitValue } from "@/lib/reports";
import { useRequireSignIn } from "@/lib/require-auth";
import { useAsync } from "@/lib/use-async";

export default function ReportPage() {
  const { reportId } = useParams<{ reportId: string }>();
  const auth = useRequireSignIn();
  const signedIn = auth.status === "signed-in";
  const data = useAsync(() => (signedIn ? api.report(reportId) : Promise.resolve(null)), `${reportId}:${signedIn}`);

  if (!signedIn || data.status === "loading" || (data.status === "success" && !data.data))
    return <LoadingState label="Loading the report" />;
  if (data.status === "error")
    return (
      <ErrorState
        title={isNotFound(data.error) ? "Report not found" : "We couldn't load this report"}
        message={isNotFound(data.error) ? "It may have been deleted." : errorMessage(data.error)}
        action={<ButtonLink href="/reports">Back to your reports</ButtonLink>}
      />
    );
  return <ReportView report={data.data!} />;
}

function Section({ id, title, children }: { id: string; title: string; children: ReactNode }) {
  return (
    <Card as="section" aria-labelledby={id}>
      <h2 id={id} className="text-xl font-semibold">
        {title}
      </h2>
      <div className="mt-3 space-y-3">{children}</div>
    </Card>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="list-disc space-y-1 pl-5">
      {items.map((x) => (
        <li key={x}>{x}</li>
      ))}
    </ul>
  );
}

function ReportView({ report }: { report: Report }) {
  const b = report.body;
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const comms = b.traits.filter((t) => t.communication);
  const refs = allReferences(b);
  const created = new Date(report.created_at).toLocaleString(undefined, { dateStyle: "long", timeStyle: "short" });

  async function download() {
    setBusy(true);
    setError(null);
    try {
      downloadBlob(await api.reportPdf(report.id), reportFilename(report.created_at));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteReport(report.id);
      router.push("/reports");
    } catch (err) {
      setError(errorMessage(err));
      setBusy(false);
    }
  }

  return (
    <article className="space-y-6">
      <header className="space-y-3">
        <p className="text-sm">
          <Link href="/reports" className="underline">
            Your reports
          </Link>
        </p>
        <h1 className="text-3xl font-bold">Your personality report</h1>
        <p className="text-sm text-ink-muted">
          Created {created} · report version {b.report_version}
        </p>
        <p className="max-w-3xl">{b.note}</p>
        <div className="flex flex-wrap gap-3">
          <Button onClick={download} disabled={busy}>
            Download PDF
          </Button>
          {!confirming && (
            <Button variant="ghost" onClick={() => setConfirming(true)} disabled={busy}>
              Delete report
            </Button>
          )}
        </div>
        {confirming && (
          <div className="rounded-card border border-line p-3" role="group" aria-label="Confirm deletion">
            <p>Delete this report? Your assessment results are kept.</p>
            <div className="mt-3 flex flex-wrap gap-3">
              <Button onClick={remove} disabled={busy}>
                Yes, delete it
              </Button>
              <Button variant="secondary" onClick={() => setConfirming(false)} disabled={busy}>
                Cancel
              </Button>
            </div>
          </div>
        )}
        {error && <FormMessage kind="error">{error}</FormMessage>}
      </header>

      {b.profile && (
        <Section id="profile" title="Profile">
          <h3 className="text-lg font-semibold">{b.profile.name}</h3>
          <p>{b.profile.summary}</p>
          <p>Your second-closest pattern is {b.profile.secondary}.</p>
          {b.profile.weak_fit && (
            <p className="text-ink-muted">
              Your answers don&apos;t match any one pattern closely, so treat this as a loose fit.
            </p>
          )}
          <p className="text-sm text-ink-muted">{b.profile.disclaimer}</p>
        </Section>
      )}

      <Section id="traits" title="Big Five traits">
        <p className="text-sm text-ink-muted">
          Scores show where you sit on the response scale, 0 to 100. They are not percentiles.
        </p>
        {b.traits.map((t) => (
          <div key={t.trait}>
            <h3 className="font-semibold">
              {t.name}: <span className="font-normal">{traitValue(t)}</span>
            </h3>
            {t.score != null && (
              <div className="relative mt-2 h-3 rounded-full bg-muted" aria-hidden>
                <div className="absolute inset-y-0 left-[40%] w-[20%] bg-line/60" />
                <div className="absolute inset-y-0 left-0 rounded-full bg-primary" style={{ width: `${t.score}%` }} />
              </div>
            )}
            <p className="mt-1 text-sm text-ink-muted">{t.description}</p>
            {t.summary && <p className="mt-1">{t.summary}</p>}
          </div>
        ))}
      </Section>

      {b.strengths.length > 0 && (
        <Section id="strengths" title="Strengths">
          <Bullets items={b.strengths} />
        </Section>
      )}
      {b.development.length > 0 && (
        <Section id="development" title="Development opportunities">
          <Bullets items={b.development} />
        </Section>
      )}

      {comms.length > 0 && (
        <Section id="communication" title="Communication">
          <h3 className="font-semibold">At work and with others</h3>
          <Bullets items={comms.map((t) => `${t.name}: ${t.communication}`)} />
          <h3 className="font-semibold">In close relationships</h3>
          <Bullets items={comms.filter((t) => t.relationships).map((t) => `${t.name}: ${t.relationships}`)} />
        </Section>
      )}

      {b.interests && (
        <Section id="interests" title="Career interests">
          {b.interests.code && b.interests.top.length > 0 ? (
            <>
              <p>Your interest code is {b.interests.code}.</p>
              <Bullets items={b.interests.top.map((a) => `${a.name} (${a.count} of ${a.total} activities): ${a.short}`)} />
              {b.interests.fields.length > 0 && <p>Fields to explore: {b.interests.fields.join(", ")}.</p>}
            </>
          ) : (
            <p>You didn&apos;t choose any activities, so there are no clear interest areas yet.</p>
          )}
          <p className="text-sm text-ink-muted">{b.interests.note}</p>
        </Section>
      )}

      {b.leadership && (
        <Section id="leadership" title="Leadership preferences">
          {b.leadership.even ? (
            <p>Your preferences are fairly even across the leadership areas.</p>
          ) : (
            <>
              <p>Most preferred: {b.leadership.most_preferred.join(", ")}.</p>
              <p>Least preferred: {b.leadership.least_preferred.join(", ")}.</p>
            </>
          )}
          <p className="text-sm text-ink-muted">{b.leadership.note}</p>
        </Section>
      )}

      <Section id="values" title="Personal values">
        <p>{b.values_note}</p>
      </Section>

      {b.plan.length > 0 && (
        <Section id="plan" title="Your development plan">
          <ol className="list-decimal space-y-2 pl-5">
            {b.plan.map((p) => (
              <li key={p.id}>
                <Link href={p.href} className="font-semibold underline">
                  {p.title}
                </Link>
                <span className="block text-sm text-ink-muted">{p.reason}</span>
              </li>
            ))}
          </ol>
        </Section>
      )}

      <Section id="methodology" title="Methodology">
        {b.methodology.map((m) => (
          <div key={m.kind} className="space-y-1">
            <h3 className="font-semibold">
              {m.instrument_name} (version {m.instrument_version})
            </h3>
            <p>{m.scoring_summary}</p>
            {m.band_note && <p className="text-sm text-ink-muted">{m.band_note}</p>}
            <p className="text-sm text-ink-muted">{m.attribution}</p>
            <p className="break-all text-xs text-ink-muted">
              Scoring engine {m.engine_version}; content {m.content_sha256.slice(0, 12)}; answers{" "}
              {m.answers_sha256.slice(0, 12)}.
            </p>
          </div>
        ))}
        {refs.length > 0 && (
          <>
            <h3 className="font-semibold">Scientific references</h3>
            <div className="text-sm text-ink-muted">
              <Bullets items={refs} />
            </div>
          </>
        )}
      </Section>

      <Section id="limitations" title="Limitations">
        <Bullets items={allLimitations(b)} />
        <p className="break-all text-xs text-ink-muted">Report fingerprint: content {b.content_sha256.slice(0, 16)}.</p>
      </Section>
    </article>
  );
}
