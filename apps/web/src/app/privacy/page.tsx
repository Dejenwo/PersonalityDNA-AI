import type { Metadata } from "next";
import { Card } from "@/components/ui";

export const metadata: Metadata = { title: "Privacy notice" };

export default function PrivacyPage() {
  return (
    <article className="mx-auto max-w-2xl space-y-4">
      <h1 className="text-3xl font-bold">Privacy notice for assessments</h1>
      <p className="text-sm text-ink-muted">Version 2026-11-26</p>
      <Card className="border-danger" role="note">
        <p className="font-semibold">Draft for development.</p>
        <p className="text-ink-muted">
          This notice describes how the current software behaves. It has not been reviewed by a lawyer and must be
          reviewed before public launch.
        </p>
      </Card>
      <h2 className="pt-4 text-xl font-semibold">What we collect</h2>
      <p>
        Your answers to assessment statements, the time you started and finished, and your confirmation that you are 18
        or older and agree to this notice. You don&apos;t need an account to take an assessment. If you create one, we
        also store your email, an optional name and a securely hashed password. If you mark learning activities as done
        (leadership or emotional awareness) or follow a growth programme, we store which activities and days you finished,
        when, and the 1 to 5 self-check ratings you choose, never anything you write about them.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Why</h2>
      <p>To calculate and show you your results. Scores are calculated by a fixed formula, not by AI.</p>
      <h2 className="pt-4 text-xl font-semibold">Who can see it</h2>
      <p>
        Your assessment is protected by a private key stored only in this browser. Anyone without that key cannot open
        your answers or results. We do not sell assessment data and do not use it to train AI models.
      </p>
      <h2 className="pt-4 text-xl font-semibold">The AI coach</h2>
      <p>
        The coach is optional and needs an account and your agreement. When you use it, your messages and, if you allow
        it, your trait scores, bands and archetype are sent to our AI provider to write replies. Your name, email
        address and individual answers are not sent. Conversations are stored encrypted, and you can delete each one or
        your whole account. We keep counts of coach usage (not message text) to manage costs and limits. If a message
        suggests you may be in danger, the app shows crisis support information instead of sending it to the AI, and
        records only that this happened. While the coach runs in demo mode, nothing is sent to an AI provider.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Your journal</h2>
      <p>
        Journal entries need an account. The title, text and tags are encrypted when stored; the date, kind of entry
        and optional mood are not. Only you can read your journal: it is never shared with other people, never shown to
        our staff and never sent to the AI coach or any AI provider. Search runs on our server after decryption and the
        words you search for are not logged. You can download your journal as Markdown or JSON, and delete single
        entries or all of them at any time.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Goals and habits</h2>
      <p>
        Goal names, reasons, milestones and habit names are encrypted when stored. We store the days you mark a habit as
        done and the dates you choose, so we can show your history. Like your journal, these are only for you and are
        included in your data download and deleted with your account.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Comparing with someone you know</h2>
      <p>
        Comparisons are optional and need both people to agree. If you invite someone or accept an invitation, the other
        person sees only whether each of your Big Five traits from your latest result is lower, middle or higher. They
        never see your scores, answers, journal or coach conversations. Either of you can end a comparison at any time,
        and then neither of you can see it. Invitation links work once and expire after 7 days.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Your choices</h2>
      <p>
        You can stop at any time. With an account you can download all your data or permanently delete your account
        and every assessment and coach conversation linked to it from the Account page.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Not a diagnosis</h2>
      <p>
        PersonalityDNA is for self-reflection. It does not diagnose any condition, and its results must not be used to
        make hiring or other decisions about people.
      </p>
    </article>
  );
}
