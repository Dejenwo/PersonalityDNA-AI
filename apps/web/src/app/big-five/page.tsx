import type { Metadata } from "next";
import Link from "next/link";
import { TrackView } from "@/components/growth-tracking";
import { ButtonLink, Card } from "@/components/ui";
import { SITE_NAME, SITE_URL } from "@/lib/site";

const TITLE = "The Big Five personality traits";
const DESCRIPTION =
  "What the Big Five traits are, what they can and can't tell you, and how PersonalityDNA measures them with public-domain IPIP items.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/big-five" },
  openGraph: { type: "article", title: TITLE, description: DESCRIPTION, url: "/big-five" },
};

const TRAITS = [
  {
    name: "Extraversion",
    high: "Energised by people and activity, talkative, quick to take the lead in groups.",
    low: "Comfortable with quiet and solitude, more reserved, recharges alone.",
  },
  {
    name: "Agreeableness",
    high: "Warm, trusting and cooperative, attentive to how others feel.",
    low: "Direct, sceptical and comfortable with disagreement or competition.",
  },
  {
    name: "Conscientiousness",
    high: "Organised, dependable and planful, likes to finish what they start.",
    low: "Flexible and spontaneous, less bound by plans and routines.",
  },
  {
    name: "Emotional stability",
    high: "Usually calm and even-tempered, recovers from setbacks fairly quickly.",
    low: "Feels worry, stress or low mood more often or more intensely.",
  },
  {
    name: "Openness (intellect and imagination)",
    high: "Curious, imaginative, drawn to new ideas, art and abstract thinking.",
    low: "Prefers the familiar and practical, values the concrete and tried-and-tested.",
  },
];

const SOURCES = [
  {
    id: "goldberg-1990",
    text: 'Goldberg, L. R. (1990). An alternative "description of personality": The Big-Five factor structure. Journal of Personality and Social Psychology, 59(6), 1216–1229.',
  },
  {
    id: "john-2008",
    text: "John, O. P., Naumann, L. P., & Soto, C. J. (2008). Paradigm shift to the integrative Big Five trait taxonomy. In O. P. John, R. W. Robins & L. A. Pervin (Eds.), Handbook of Personality: Theory and Research (3rd ed., pp. 114–158). Guilford Press.",
  },
  {
    id: "goldberg-2006",
    text: "Goldberg, L. R., Johnson, J. A., Eber, H. W., Hogan, R., Ashton, M. C., Cloninger, C. R., & Gough, H. G. (2006). The International Personality Item Pool and the future of public-domain personality measures. Journal of Research in Personality, 40(1), 84–96.",
  },
  {
    id: "donnellan-2006",
    text: "Donnellan, M. B., Oswald, F. L., Baird, B. M., & Lucas, R. E. (2006). The Mini-IPIP scales: Tiny-yet-effective measures of the Big Five factors of personality. Psychological Assessment, 18(2), 192–203.",
  },
  {
    id: "roberts-2006",
    text: "Roberts, B. W., Walton, K. E., & Viechtbauer, W. (2006). Patterns of mean-level change in personality traits across the life course: A meta-analysis of longitudinal studies. Psychological Bulletin, 132(1), 1–25.",
  },
];

function Cite({ id, n }: { id: string; n: number }) {
  return (
    <sup>
      <a href={`#source-${id}`} className="text-primary underline" aria-label={`Source ${n}`}>
        [{n}]
      </a>
    </sup>
  );
}

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "Article",
  headline: TITLE,
  description: DESCRIPTION,
  url: `${SITE_URL}/big-five`,
  publisher: { "@type": "Organization", name: SITE_NAME, url: SITE_URL },
};

export default function BigFivePage() {
  return (
    <article className="mx-auto max-w-3xl space-y-10">
      <TrackView event="big_five_article_view" />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <header>
        <h1 className="text-3xl font-bold">{TITLE}</h1>
        <p className="mt-3 text-lg text-ink-muted">
          The Big Five is the most widely used framework in personality research. It describes personality with five
          broad dimensions, each running from one end to the other, rather than sorting people into types.
          <Cite id="john-2008" n={2} />
        </p>
      </header>

      <section aria-labelledby="where-heading" className="space-y-3">
        <h2 id="where-heading" className="text-2xl font-semibold">
          Where it comes from
        </h2>
        <p>
          Researchers noticed that the many words people use to describe each other cluster into a small number of
          groups. Across studies with different word lists and questionnaires, five broad factors kept appearing.
          <Cite id="goldberg-1990" n={1} /> Later work showed the same five dimensions in many questionnaires and
          languages, which is why the model became a common reference point for researchers.
          <Cite id="john-2008" n={2} />
        </p>
      </section>

      <section aria-labelledby="traits-heading" className="space-y-4">
        <h2 id="traits-heading" className="text-2xl font-semibold">
          The five traits
        </h2>
        <p>
          Each trait is a continuum. Most people score somewhere in the middle, and both ends have advantages and costs
          depending on the situation. Neither end is better.
        </p>
        <ul className="space-y-3">
          {TRAITS.map((t) => (
            <li key={t.name}>
              <Card as="div">
                <h3 className="text-lg font-semibold">{t.name}</h3>
                <dl className="mt-2 grid gap-2 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="font-medium">Toward the higher end</dt>
                    <dd className="text-ink-muted">{t.high}</dd>
                  </div>
                  <div>
                    <dt className="font-medium">Toward the lower end</dt>
                    <dd className="text-ink-muted">{t.low}</dd>
                  </div>
                </dl>
              </Card>
            </li>
          ))}
        </ul>
        <p className="text-sm text-ink-muted">
          Some questionnaires measure the opposite end of emotional stability and call it neuroticism. It is the same
          dimension described from the other side.
        </p>
      </section>

      <section aria-labelledby="change-heading" className="space-y-3">
        <h2 id="change-heading" className="text-2xl font-semibold">
          Traits are tendencies, not fixed labels
        </h2>
        <p>
          Your scores describe how you tend to think, feel and act across many situations, not what you will do in any
          one moment. Personality is fairly stable, but it does change across adulthood: on average, people become more
          conscientious, more agreeable and more emotionally stable as they get older.
          <Cite id="roberts-2006" n={5} /> Habits and deliberate practice can shift how you behave even where your
          underlying tendencies stay similar.
        </p>
      </section>

      <section aria-labelledby="limits-heading" className="space-y-3">
        <h2 id="limits-heading" className="text-2xl font-semibold">
          What it can&apos;t tell you
        </h2>
        <ul className="list-disc space-y-2 ps-6">
          <li>It is not a clinical assessment and can&apos;t diagnose any mental health condition.</li>
          <li>It doesn&apos;t measure ability, intelligence, values or worth.</li>
          <li>It should not be used to decide whether to hire, promote or reject someone.</li>
          <li>
            A self-report questionnaire reflects how you see yourself today. Your mood, context and the way you read the
            questions all affect it.
          </li>
        </ul>
      </section>

      <section aria-labelledby="how-heading" className="space-y-3">
        <h2 id="how-heading" className="text-2xl font-semibold">
          How PersonalityDNA measures it
        </h2>
        <p>
          Our assessments use items from the International Personality Item Pool (IPIP), a public-domain collection of
          personality items created so that research-quality measures could be freely used.
          <Cite id="goldberg-2006" n={3} /> The quick assessment uses the 20-item Mini-IPIP
          <Cite id="donnellan-2006" n={4} /> and the comprehensive assessment uses the 50-item IPIP Big-Five factor
          markers. Scores are calculated with a fixed, published method, with no AI involved, and you can see how each
          score was worked out.
        </p>
        <p>
          We show your scores on the questionnaire&apos;s own scale. We don&apos;t show percentiles or compare you with
          a population, because we don&apos;t yet have norm data to do that honestly.
        </p>
        <div className="flex flex-wrap gap-3 pt-2">
          <ButtonLink href="/discover">Take the free assessment</ButtonLink>
          <ButtonLink href="/privacy" variant="secondary">
            How we handle your answers
          </ButtonLink>
        </div>
      </section>

      <section aria-labelledby="sources-heading" className="space-y-3 border-t border-line pt-6">
        <h2 id="sources-heading" className="text-xl font-semibold">
          Sources
        </h2>
        <ol className="list-decimal space-y-2 ps-6 text-sm text-ink-muted">
          {SOURCES.map((s) => (
            <li key={s.id} id={`source-${s.id}`}>
              {s.text}
            </li>
          ))}
        </ol>
        <p className="text-sm text-ink-muted">
          Looking for practical next steps? Browse <Link href="/learn" className="text-primary underline">Learn</Link>.
        </p>
      </section>
    </article>
  );
}
