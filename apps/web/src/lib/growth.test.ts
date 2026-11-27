import type { GrowthProgram } from "@pdna/api-client";
import { describe, expect, it } from "vitest";
import { allDays, dayTitle, lengthLabel, percentDone, weekOfDay, withDay, withRating } from "./growth";

const day = (n: number, kind: "lesson" | "exercise" | "milestone" | "review") => ({
  day: n,
  kind,
  text: `d${n}`,
  completed_at: null,
});

const program = {
  weeks: [{ number: 1, rating: null, days: [day(1, "lesson"), day(2, "exercise"), day(7, "milestone")] }],
  review_days: [day(8, "review")],
  enrollment: { started_at: "t0", completed_at: null, days_done: 0, next_day: 1 },
} as unknown as GrowthProgram;

describe("growth helpers", () => {
  it("labels lengths", () => {
    expect(lengthLabel(7)).toBe("7-day challenge");
    expect(lengthLabel(90)).toBe("90-day programme");
  });

  it("computes percentages safely", () => {
    expect(percentDone(0, 30)).toBe(0);
    expect(percentDone(10, 30)).toBe(33);
    expect(percentDone(40, 30)).toBe(100);
    expect(percentDone(1, 0)).toBe(0);
  });

  it("titles days and finds their week", () => {
    expect(dayTitle(day(3, "exercise"))).toBe("Day 3 · Practise");
    expect(allDays(program).map((d) => d.day)).toEqual([1, 2, 7, 8]);
    expect(weekOfDay(program, 7)).toBe(1);
    expect(weekOfDay(program, 8)).toBeNull();
  });

  it("updates progress locally after marking days", () => {
    let p = withDay(program, 1, true, "t1");
    expect(p.enrollment).toMatchObject({ days_done: 1, next_day: 2, completed_at: null });
    expect(withDay(p, 1, true, "t2").weeks[0]!.days[0]!.completed_at).toBe("t1"); // keeps the first time
    for (const d of [2, 7, 8]) p = withDay(p, d, true, "t3");
    expect(p.enrollment).toMatchObject({ days_done: 4, next_day: null, completed_at: "t3" });
    p = withDay(p, 2, false, "t4");
    expect(p.enrollment).toMatchObject({ days_done: 3, next_day: 2, completed_at: null });
    expect(program.enrollment!.days_done).toBe(0); // the original is not changed
  });

  it("sets a week's rating", () => {
    expect(withRating(program, 1, 4).weeks[0]!.rating).toBe(4);
    expect(program.weeks[0]!.rating).toBeNull();
  });
});
