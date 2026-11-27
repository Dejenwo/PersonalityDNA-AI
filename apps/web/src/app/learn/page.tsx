import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = { title: "Learn" };

const TRACKS = [
  {
    href: "/growth",
    title: "Growth programmes",
    text: "Seven-day challenges and 30, 60 and 90-day programmes with a short exercise each day, weekly milestones and self-checks.",
  },
  {
    href: "/emotional-awareness",
    title: "Emotional awareness",
    text: "Notice and name feelings, pause before you respond, listen to understand and say what you need. Seven modules.",
  },
  {
    href: "/leadership",
    title: "Leadership development",
    text: "The people side of leading: direction, delegation, feedback, decisions and conflict. Nine modules, with an optional questionnaire to suggest where to start.",
  },
];

export default function LearnPage() {
  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-3xl font-bold">Learn</h1>
        <p className="mt-2 max-w-2xl text-ink-muted">
          Day-by-day programmes, and short modules with ideas to read, small activities to try in everyday life and
          questions to reflect on. Sign in to keep track of what you finish.
        </p>
      </header>
      <ul className="grid gap-4 sm:grid-cols-2">
        {TRACKS.map((t) => (
          <li key={t.href}>
            <Link href={t.href} className="block h-full rounded-card border border-line bg-surface p-5 hover:bg-muted">
              <span className="block text-xl font-semibold">{t.title}</span>
              <span className="mt-1 block text-ink-muted">{t.text}</span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
