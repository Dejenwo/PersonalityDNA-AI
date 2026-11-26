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
        or older and agree to this notice. We do not ask for your name or email to take an assessment.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Why</h2>
      <p>To calculate and show you your results. Scores are calculated by a fixed formula, not by AI.</p>
      <h2 className="pt-4 text-xl font-semibold">Who can see it</h2>
      <p>
        Your assessment is protected by a private key stored only in this browser. Anyone without that key cannot open
        your answers or results. We do not sell assessment data and do not use it to train AI models.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Your choices</h2>
      <p>
        You can stop at any time. Account features for exporting and deleting your data are planned and will be listed
        here when available.
      </p>
      <h2 className="pt-4 text-xl font-semibold">Not a diagnosis</h2>
      <p>
        PersonalityDNA is for self-reflection. It does not diagnose any condition, and its results must not be used to
        make hiring or other decisions about people.
      </p>
    </article>
  );
}
