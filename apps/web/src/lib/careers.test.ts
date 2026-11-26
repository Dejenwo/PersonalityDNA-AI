import { describe, expect, it } from "vitest";
import { latestByFamily, workingStyleQuestions } from "./careers";

const families = { "mini-ipip-20": "big_five", "ipip-neo-120": "big_five", "onet-ipsf-60": "interests" };

describe("latestByFamily", () => {
  it("picks the newest result of each family and ignores unknown instruments", () => {
    const out = latestByFamily(
      [
        { instrumentId: "mini-ipip-20", resultId: "a", at: "2026-01-01T00:00:00Z" },
        { instrumentId: "ipip-neo-120", resultId: "b", at: "2026-03-01T00:00:00Z" },
        { instrumentId: "onet-ipsf-60", resultId: "c", at: "2026-02-01T00:00:00Z" },
        { instrumentId: "retired", resultId: "d", at: "2026-04-01T00:00:00Z" },
      ],
      families,
    );
    expect(out.big_five?.resultId).toBe("b");
    expect(out.interests?.resultId).toBe("c");
  });

  it("returns nothing when there are no results", () => {
    expect(latestByFamily([], families)).toEqual({});
  });
});

describe("workingStyleQuestions", () => {
  it("asks about higher and lower bands only", () => {
    const qs = workingStyleQuestions([
      { trait: "extraversion", band: "higher" },
      { trait: "openness", band: "middle" },
      { trait: "conscientiousness", band: "lower" },
      { trait: "agreeableness", band: null },
      { trait: "unknown", band: "higher" },
    ]);
    expect(qs).toHaveLength(2);
    expect(qs[0]).toMatch(/contact with other people/);
    expect(qs[1]).toMatch(/flexibility/);
  });
});
