import { describe, expect, it } from "vitest";
import { historyLabel, scheduleLabel } from "./habits";

const w = (planned: number, done_on_planned: number, done_extra = 0) => ({
  last_30: { days: 30, planned, done_on_planned, done_extra },
});

describe("habit helpers", () => {
  it("labels schedules", () => {
    expect(scheduleLabel([6, 5, 4, 3, 2, 1, 0])).toBe("Every day");
    expect(scheduleLabel([0, 1, 2, 3, 4])).toBe("Weekdays");
    expect(scheduleLabel([6, 5])).toBe("Weekends");
    expect(scheduleLabel([4, 0, 2])).toBe("Mon, Wed, Fri");
  });

  it("summarises history neutrally", () => {
    expect(historyLabel(w(0, 0))).toBe("No planned days yet in the last 30 days.");
    expect(historyLabel(w(1, 1))).toBe("Done on 1 of 1 planned day in the last 30 days.");
    expect(historyLabel(w(12, 7, 2))).toBe("Done on 7 of 12 planned days in the last 30 days, plus 2 extra days.");
  });
});
