import { describe, expect, it } from "vitest";
import { formatEntryDate, localToday, parseTags, preview } from "./journal";

describe("journal helpers", () => {
  it("parses tags", () => {
    expect(parseTags(" Work, #work,  deep   focus ,, Family")).toEqual(["work", "deep focus", "family"]);
    expect(parseTags("")).toEqual([]);
  });

  it("formats dates without shifting the day", () => {
    expect(formatEntryDate("2026-03-03")).toMatch(/^Tuesday,? 3 March 2026$/); // comma varies by ICU version
    expect(localToday(new Date(2026, 0, 5, 23, 30))).toBe("2026-01-05");
  });

  it("previews long text", () => {
    expect(preview("short\n\ntext")).toBe("short text");
    const p = preview("word ".repeat(100), 20);
    expect(p.length).toBeLessThanOrEqual(20);
    expect(p.endsWith("…")).toBe(true);
  });
});
