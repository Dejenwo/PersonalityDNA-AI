import type { ReportBody } from "@pdna/api-client";
import { describe, expect, it } from "vitest";
import { allLimitations, allReferences, kindsLabel, reportFilename, traitValue } from "./reports";

type Trait = ReportBody["traits"][number];
const trait = (over: Partial<Trait>): Trait => ({
  trait: "openness",
  name: "Openness",
  description: "",
  score: 57.4,
  band: "middle",
  summary: null,
  communication: null,
  relationships: null,
  ...over,
});

describe("reports", () => {
  it("labels the assessments a report uses", () => {
    expect(kindsLabel(["big_five", "interests"])).toBe("Big Five traits, Career interests");
  });

  it("names the PDF by local date", () => {
    const d = new Date(2026, 10, 3, 9, 30);
    expect(reportFilename(d.toISOString())).toBe("personality-report-2026-11-03.pdf");
  });

  it("prints each score as text", () => {
    expect(traitValue(trait({}))).toBe("57 out of 100, Middle band");
    expect(traitValue(trait({ score: null, band: null }))).toBe("Not scored");
  });

  it("merges limitations and references without repeats", () => {
    const m = (limitations: string[], references: string[]) =>
      ({ limitations, references }) as unknown as ReportBody["methodology"][number];
    const body = {
      limitations: ["General"],
      methodology: [m(["Self-report", "General"], ["B", "A"]), m(["Self-report"], ["A"])],
    } as unknown as ReportBody;
    expect(allLimitations(body)).toEqual(["General", "Self-report"]);
    expect(allReferences(body)).toEqual(["A", "B"]);
  });
});
