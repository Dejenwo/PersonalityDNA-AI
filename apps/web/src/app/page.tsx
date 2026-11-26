import { ButtonLink, Card } from "@/components/ui";

const points = [
  {
    title: "Grounded in research",
    body: "Built on Big Five items from the public-domain International Personality Item Pool, scored with a published, deterministic method.",
  },
  {
    title: "Honest about limits",
    body: "We show what your answers say, explain how scores are calculated, and never present a personality type as a fixed label.",
  },
  {
    title: "Private by default",
    body: "No account needed to start. Your answers are tied to this device until you choose otherwise, and we never sell assessment data.",
  },
];

export default function HomePage() {
  return (
    <>
      <section className="py-10 sm:py-16">
        <p className="text-sm font-semibold uppercase tracking-wide text-accent">PersonalityDNA AI</p>
        <h1 className="mt-3 max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">
          Discover yourself. Understand others. Grow with intention.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-ink-muted">
          Take a free Big Five personality assessment and get a clear, balanced picture of your tendencies, your
          strengths and the areas you might want to develop.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <ButtonLink href="/discover">Start free assessment</ButtonLink>
          <ButtonLink href="/history" variant="secondary">
            Continue where I left off
          </ButtonLink>
        </div>
      </section>
      <section aria-labelledby="why" className="grid gap-4 sm:grid-cols-3">
        <h2 id="why" className="sr-only">
          Why PersonalityDNA
        </h2>
        {points.map((p) => (
          <Card key={p.title} as="article">
            <h3 className="text-lg font-semibold">{p.title}</h3>
            <p className="mt-2 text-ink-muted">{p.body}</p>
          </Card>
        ))}
      </section>
    </>
  );
}
