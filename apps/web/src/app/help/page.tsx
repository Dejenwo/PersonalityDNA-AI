import type { Metadata } from "next";
import Link from "next/link";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Help",
  description: "Answers to common questions about PersonalityDNA: results, privacy, your account, plans and the AI coach.",
  alternates: { canonical: "/help" },
};

const SUPPORT_EMAIL = process.env.NEXT_PUBLIC_SUPPORT_EMAIL;

const SECTIONS: { title: string; items: { q: string; a: ReactNode }[] }[] = [
  {
    title: "About your results",
    items: [
      {
        q: "What does PersonalityDNA measure?",
        a: (
          <>
            The Big Five personality traits, using public-domain questionnaires from the International Personality
            Item Pool. You can also explore career interests and leadership preferences. Read{" "}
            <Link className="underline" href="/big-five">
              how the Big Five works
            </Link>
            .
          </>
        ),
      },
      {
        q: "Is this a clinical or diagnostic test?",
        a: "No. It is for self-reflection and personal development. It can't diagnose any condition and must not be used to make hiring or other decisions about people.",
      },
      {
        q: "How are my scores worked out?",
        a: "Each trait score is the average of your answers to that trait's statements, shown on a 0 to 100 scale. The same answers always give the same scores; no AI is involved in scoring.",
      },
      {
        q: "Why don't you show percentiles or say how I compare with others?",
        a: "Comparing you with other people needs data from a large, described group of people, which we don't have yet. Your bands (lower, middle, higher) describe where your answers sit on the scale, not a ranking.",
      },
      {
        q: "My result surprised me. Is it wrong?",
        a: "Questionnaires reflect how you described yourself on the day, so results can shift with mood and context. Treat them as a starting point for reflection. You can take the assessment again at any time and compare results in your history.",
      },
    ],
  },
  {
    title: "Privacy and your data",
    items: [
      {
        q: "Who can see my answers, journal and coaching conversations?",
        a: "Only you. Journal entries, goals, reports and coaching messages are encrypted when stored, and our staff tools never show them. Nothing is shared with anyone unless you choose to, for example by creating a share card or comparing with someone.",
      },
      {
        q: "How do I download my data?",
        a: (
          <>
            Go to{" "}
            <Link className="underline" href="/account">
              your account
            </Link>{" "}
            and choose Download my data. You get everything we store about you as a file.
          </>
        ),
      },
      {
        q: "How do I delete my account?",
        a: "In your account, choose Delete my account and confirm. Your answers, results, journal, goals, reports, coaching and other data are deleted straight away. If you subscribed, cancel the subscription first so you aren't charged again.",
      },
      {
        q: "Do you use trackers or sell data?",
        a: (
          <>
            No. We only count a few anonymous events per day, such as how many assessments were started, with no identifier, and we never sell data. See the{" "}
            <Link className="underline" href="/privacy">
              privacy notice
            </Link>
            .
          </>
        ),
      },
    ],
  },
  {
    title: "Account and plans",
    items: [
      {
        q: "Do I need an account?",
        a: "No. You can take an assessment and see your result without one. An account keeps your results safe across devices and unlocks the journal, goals, reports and coach.",
      },
      {
        q: "I didn't get the confirmation or password reset email.",
        a: "Check your spam folder, then ask for a new link. Links expire: confirmation links after 24 hours and password reset links after 60 minutes.",
      },
      {
        q: "How do I change or cancel my subscription?",
        a: (
          <>
            If you subscribed on the website, use Manage or cancel subscription on{" "}
            <Link className="underline" href="/account">
              your account page
            </Link>
            . If you subscribed in the app, change it in the App Store or Google Play settings. See{" "}
            <Link className="underline" href="/pricing">
              plans and pricing
            </Link>
            .
          </>
        ),
      },
    ],
  },
  {
    title: "The AI coach",
    items: [
      {
        q: "Is the coach a person or a therapist?",
        a: "Neither. It is an AI that helps you reflect on your results and everyday situations. It can make mistakes, it isn't a licensed professional, and it shouldn't be relied on for medical, legal or financial advice.",
      },
      {
        q: "What does the coach know about me?",
        a: "Only the results you choose to share when you start a conversation, such as your trait scores and bands, and what you write. It never sees your individual answers, your journal or your email address.",
      },
    ],
  },
];

const slug = (title: string) => `help-${title.toLowerCase().replace(/[^a-z]+/g, "-")}`;

export default function HelpPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-10">
      <header>
        <h1 className="text-3xl font-bold">Help</h1>
        <p className="mt-2 text-ink-muted">Answers to common questions. Can&apos;t find yours? Contact us below.</p>
      </header>

      <section aria-labelledby="urgent-heading" className="rounded-card border border-line bg-muted p-5">
        <h2 id="urgent-heading" className="text-xl font-semibold">
          If you need urgent help
        </h2>
        <p className="mt-2">PersonalityDNA can&apos;t help in a crisis. Please reach out to people who can:</p>
        <ul className="mt-2 list-disc space-y-1 pl-6">
          <li>If you or anyone else is in immediate danger, call your local emergency number now.</li>
          <li>In the US or Canada, call or text 988 to reach a crisis line.</li>
          <li>In the UK or Ireland, call Samaritans free on 116 123.</li>
          <li>
            Anywhere else,{" "}
            <a className="underline" href="https://findahelpline.com" rel="noopener noreferrer" target="_blank">
              findahelpline.com
            </a>{" "}
            lists free, confidential helplines in your country.
          </li>
        </ul>
      </section>

      {SECTIONS.map((section) => (
        <section key={section.title} aria-labelledby={slug(section.title)}>
          <h2 id={slug(section.title)} className="text-xl font-semibold">
            {section.title}
          </h2>
          <div className="mt-3 space-y-2">
            {section.items.map((item) => (
              <details key={item.q} className="rounded-card border border-line bg-surface p-4">
                <summary className="cursor-pointer font-medium">{item.q}</summary>
                <div className="mt-2 text-ink-muted">{item.a}</div>
              </details>
            ))}
          </div>
        </section>
      ))}

      <section aria-labelledby="contact-heading">
        <h2 id="contact-heading" className="text-xl font-semibold">
          Contact us
        </h2>
        <p className="mt-2">
          Report a problem or send an idea with the{" "}
          <Link className="underline" href="/feedback?from=/help">
            feedback form
          </Link>
          .
          {SUPPORT_EMAIL && (
            <>
              {" "}
              For questions about your account or a payment, email{" "}
              <a className="underline" href={`mailto:${SUPPORT_EMAIL}`}>
                {SUPPORT_EMAIL}
              </a>
              . Please don&apos;t send passwords.
            </>
          )}
        </p>
      </section>
    </div>
  );
}
