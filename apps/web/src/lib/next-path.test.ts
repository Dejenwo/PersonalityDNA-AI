import { describe, expect, it } from "vitest";
import { safeNextPath } from "./next-path";

describe("safeNextPath", () => {
  it("allows same-site paths", () => {
    expect(safeNextPath("?next=/coach")).toBe("/coach");
    expect(safeNextPath("?next=%2Fcoach%3Fresult%3D1")).toBe("/coach?result=1");
  });
  it("rejects other sites and falls back", () => {
    expect(safeNextPath("")).toBe("/history");
    expect(safeNextPath("?next=https://evil.example")).toBe("/history");
    expect(safeNextPath("?next=//evil.example")).toBe("/history");
    expect(safeNextPath("?next=/\\evil.example")).toBe("/history");
  });
});
