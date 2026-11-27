import type { InterestsOut, LeadershipOut, Methodology, ResultOut } from "@pdna/api-client";
import Link from "next/link";
import { ButtonLink, Card } from "./ui";

export function MethodSection({ m }: { m: Methodology }) {
  return (
    <section aria-labelledby="method">
      <h2 id="method" className="text-2xl font-bold">
        How this was calculated
      </h2>
      <Card className="mt-4 space-y-3 text-ink-muted">
        <p>{m.scoring_summary}</p>
        <p>{m.band_note}</p>
        <h3 className="pt-2 font-semibold text-ink">Limitations</h3>
        <ul className="list-disc space-y-1 ps-5">
          {m.limitations.map((l) => (
            <li key={l}>{l}</li>
          ))}
        </ul>
        <details className="pt-2">
          <summary className="cursor-pointer font-semibold text-ink">References and audit details</summary>
          <ul className="mt-2 list-disc space-y-1 ps-5 text-sm">
            {m.references.map((ref) => (
              <li key={ref}>{ref}</li>
            ))}
          </ul>
          <p className="mt-2 text-sm">{m.attribution}</p>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 text-xs break-all">
            <dt>Instrument</dt>
            <dd>
              {m.instrument_name} ({m.instrument_id} v{m.instrument_version})
            </dd>
            <dt>Scoring engine</dt>
            <dd>v{m.engine_version}</dd>
            <dt>Content hash</dt>
            <dd>{m.content_sha256}</dd>
            <dt>Answers hash</dt>
            <dd>{m.answers_sha256}</dd>
          </dl>
        </details>
      </Card>
    </section>
  );
}

export function InterestResults({ r, interests }: { r: ResultOut; interests: InterestsOut }) {
  const top = interests.areas.slice(0, 3);
  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">Your career interests</p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
          {interests.empty ? "No clear interest areas yet" : `Interest code ${interests.code}`}
        </h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          {interests.empty
            ? "You didn't choose any of the activities, so there is no ranking to show. You could retake it and choose anything that sounds even a little appealing."
            : `Your strongest interest areas are ${top.map((a) => a.name).join(", ")}. Interests describe what appeals to you, not what you are good at or which job you should do.`}
        </p>
      </header>

      {interests.draft && (
        <Card role="note" className="border-accent">
          <h2 className="font-semibold">Preview</h2>
          <p className="mt-1 text-ink-muted">
            This assessment is in preview while its wording is checked against the official source. Treat these results
            as a test.
          </p>
        </Card>
      )}

      {!interests.empty && interests.boundary_ties.length > 0 && (
        <Card role="note">
          <p className="text-ink-muted">
            {interests.boundary_ties.join(", ")} are tied around third place, so your code could reasonably use any of
            them. Pick the one whose activities feel most like you.
          </p>
        </Card>
      )}

      <section aria-labelledby="areas">
        <h2 id="areas" className="text-2xl font-bold">
          Your six interest areas
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Each bar counts the activities you said you would like to do, out of 10. It does not compare you with anyone else.
        </p>
        <Card className="mt-4 space-y-4">
          {interests.areas.map((a) => (
            <div key={a.area}>
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-semibold">
                  {a.name} <span className="text-ink-muted">({a.letter})</span>
                </span>
                <span className="text-sm text-ink-muted">
                  {a.count} of {a.total}
                </span>
              </div>
              <div
                role="img"
                aria-label={`${a.name}: ${a.count} of ${a.total} activities chosen`}
                className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted"
              >
                <div className="h-full rounded-full bg-accent" style={{ width: `${a.score}%` }} />
              </div>
            </div>
          ))}
        </Card>
      </section>

      {!interests.empty && (
        <section aria-labelledby="explore" className="space-y-4">
          <h2 id="explore" className="text-2xl font-bold">
            Explore your top areas
          </h2>
          {top.map((a) => (
            <Card key={a.area} as="article">
              <h3 className="text-xl font-semibold">{a.name}</h3>
              <p className="mt-1">{a.short}</p>
              <div className="mt-3 grid gap-4 sm:grid-cols-2">
                <div>
                  <h4 className="font-semibold">You may enjoy</h4>
                  <ul className="mt-1 list-disc ps-5 text-ink-muted">
                    {a.enjoys.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>
                <div>
                  <h4 className="font-semibold">Fields to explore</h4>
                  <ul className="mt-1 list-disc ps-5 text-ink-muted">
                    {a.fields.map((x) => (
                      <li key={x}>{x}</li>
                    ))}
                  </ul>
                </div>
              </div>
              <p className="mt-3 text-sm">
                <span className="font-semibold">To reflect on:</span> {a.reflection}
              </p>
            </Card>
          ))}
          <Card>
            <h3 className="font-semibold">Look up real occupations</h3>
            <ul className="mt-2 space-y-1">
              {interests.explore_links.map((l) => (
                <li key={l.url}>
                  <a className="underline" href={l.url} target="_blank" rel="noopener noreferrer">
                    {l.label}
                  </a>
                </li>
              ))}
            </ul>
          </Card>
        </section>
      )}

      <MethodSection m={r.methodology} />

      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/careers">Career exploration</ButtonLink>
        <ButtonLink href={`/coach?result=${encodeURIComponent(r.id)}`} variant="secondary">
          Talk it through with the coach
        </ButtonLink>
        <ButtonLink href="/history" variant="secondary">
          My results
        </ButtonLink>
      </div>
    </div>
  );
}

export function LeadershipAreas({ leadership }: { leadership: LeadershipOut }) {
  return (
    <Card className="space-y-4">
      {leadership.areas.map((a) => (
        <div key={a.area}>
          <div className="flex items-baseline justify-between gap-3">
            <span className="font-semibold">{a.name}</span>
            <span className="text-sm text-ink-muted">{Math.round(a.score)}</span>
          </div>
          <div
            role="img"
            aria-label={`${a.name}: ${Math.round(a.score)} out of 100`}
            className="mt-1 h-2 w-full overflow-hidden rounded-full bg-muted"
          >
            <div className="h-full rounded-full bg-accent" style={{ width: `${a.score}%` }} />
          </div>
          <p className="mt-1 text-sm text-ink-muted">{a.text}</p>
        </div>
      ))}
    </Card>
  );
}

export function RecommendedModules({ leadership }: { leadership: LeadershipOut }) {
  return (
    <ul className="grid gap-4 sm:grid-cols-3">
      {leadership.recommended_modules.map((m) => (
        <li key={m.id}>
          <Card as="article" className="flex h-full flex-col">
            <p className="text-sm font-semibold text-accent">
              {m.reason === "build" ? "Build on a strength" : "Stretch yourself"}
            </p>
            <h3 className="mt-1 text-lg font-semibold">{m.title}</h3>
            <p className="mt-1 flex-1 text-sm text-ink-muted">{m.summary}</p>
            <Link href={`/leadership/${m.id}`} className="mt-3 text-primary underline">
              Open {m.title}
            </Link>
          </Card>
        </li>
      ))}
    </ul>
  );
}

export function LeadershipResults({ r, leadership }: { r: ResultOut; leadership: LeadershipOut }) {
  const names = Object.fromEntries(leadership.areas.map((a) => [a.area, a.name]));
  return (
    <div className="space-y-8">
      <header>
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">Your leadership preferences</p>
        <h1 className="mt-2 text-3xl font-bold sm:text-4xl">
          {leadership.even ? "An even spread of preferences" : `You lean towards ${names[leadership.top[0]!]}`}
        </h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          {leadership.even
            ? "You enjoy most leadership activities about equally, so no single preference stands out."
            : `Your strongest preferences are ${leadership.top.map((a) => names[a]).join(", ")}.`}{" "}
          {leadership.note}
        </p>
      </header>

      <section aria-labelledby="areas">
        <h2 id="areas" className="text-2xl font-bold">
          Your nine leadership areas
        </h2>
        <p className="mt-1 text-sm text-ink-muted">
          Most to least preferred. Scores compare your areas with each other only, not with other people.
        </p>
        <div className="mt-4">
          <LeadershipAreas leadership={leadership} />
        </div>
      </section>

      <section aria-labelledby="modules" className="space-y-4">
        <h2 id="modules" className="text-2xl font-bold">
          Suggested development modules
        </h2>
        <RecommendedModules leadership={leadership} />
      </section>

      <MethodSection m={r.methodology} />

      <div className="flex flex-wrap gap-3">
        <ButtonLink href="/leadership">All leadership modules</ButtonLink>
        <ButtonLink href={`/coach?topic=leadership&result=${encodeURIComponent(r.id)}`} variant="secondary">
          Talk it through with the coach
        </ButtonLink>
      </div>
    </div>
  );
}
