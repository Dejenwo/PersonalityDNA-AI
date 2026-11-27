import type { ReportBody, ReportSummary } from "@pdna/api-client";

export const BAND_LABEL = { lower: "Lower", middle: "Middle", higher: "Higher" } as const;

const KIND_LABEL: Record<ReportSummary["kinds"][number], string> = {
  big_five: "Big Five traits",
  interests: "Career interests",
  leadership: "Leadership preferences",
};

/** "Big Five traits, Career interests" for the assessments a report draws on. */
export function kindsLabel(kinds: ReportSummary["kinds"]): string {
  return kinds.map((k) => KIND_LABEL[k]).join(", ");
}

/** File name for a report's PDF, using the date in the person's own time zone. */
export function reportFilename(createdAt: string): string {
  const d = new Date(createdAt);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `personality-report-${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}.pdf`;
}

/** "57 out of 100, Middle band" or "Not scored": the text that goes with each bar. */
export function traitValue(t: ReportBody["traits"][number]): string {
  return t.score != null && t.band ? `${Math.round(t.score)} out of 100, ${BAND_LABEL[t.band]} band` : "Not scored";
}

/** Limitations from the report and every instrument, without repeats, in order. */
export function allLimitations(body: ReportBody): string[] {
  return [...new Set([...body.limitations, ...body.methodology.flatMap((m) => m.limitations)])];
}

/** Scientific references across the instruments, sorted and without repeats. */
export function allReferences(body: ReportBody): string[] {
  return [...new Set(body.methodology.flatMap((m) => m.references))].sort();
}
