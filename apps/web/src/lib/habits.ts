import type { Habit } from "@pdna/api-client";

export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const SHORT = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** "Every day", "Weekdays", "Weekends" or a list such as "Mon, Wed, Fri". */
export function scheduleLabel(weekdays: number[]): string {
  const days = [...new Set(weekdays)].sort((a, b) => a - b);
  if (days.length === 7) return "Every day";
  if (days.join() === "0,1,2,3,4") return "Weekdays";
  if (days.join() === "5,6") return "Weekends";
  return days.map((d) => SHORT[d]).join(", ");
}

/**
 * A neutral summary of the last 30 days. No streaks and no judgement: missing days are simply not counted.
 */
export function historyLabel(h: Pick<Habit, "last_30">): string {
  const w = h.last_30;
  if (w.planned === 0 && w.done_extra === 0) return "No planned days yet in the last 30 days.";
  const base = `Done on ${w.done_on_planned} of ${w.planned} planned day${w.planned === 1 ? "" : "s"} in the last 30 days`;
  return w.done_extra > 0 ? `${base}, plus ${w.done_extra} extra day${w.done_extra === 1 ? "" : "s"}.` : `${base}.`;
}
