import type { GrowthProgram } from "@pdna/api-client";

type Day = GrowthProgram["review_days"][number];

/** "7-day challenge" or "30-day programme". */
export function lengthLabel(days: number): string {
  return days === 7 ? "7-day challenge" : `${days}-day programme`;
}

/** Whole-number percentage of days done, for progress bars. */
export function percentDone(done: number, total: number): number {
  if (total <= 0) return 0;
  return Math.min(100, Math.round((done / total) * 100));
}

const KIND_LABEL: Record<Day["kind"], string> = {
  lesson: "Learn",
  exercise: "Practise",
  milestone: "Milestone",
  review: "Review",
};

export function dayTitle(day: Day): string {
  return `Day ${day.day} · ${KIND_LABEL[day.kind]}`;
}

/** All days of a programme in order. */
export function allDays(p: GrowthProgram): Day[] {
  return [...p.weeks.flatMap((w) => w.days), ...p.review_days];
}

/** The week that holds a day, or null for review days. */
export function weekOfDay(p: GrowthProgram, day: number): number | null {
  return p.weeks.find((w) => w.days.some((d) => d.day === day))?.number ?? null;
}

/** The programme with one day marked done or not done, and the enrolment summary updated to match. */
export function withDay(p: GrowthProgram, day: number, done: boolean, now: string): GrowthProgram {
  const mark = (d: Day): Day => (d.day === day ? { ...d, completed_at: done ? (d.completed_at ?? now) : null } : d);
  const next: GrowthProgram = {
    ...p,
    weeks: p.weeks.map((w) => ({ ...w, days: w.days.map(mark) })),
    review_days: p.review_days.map(mark),
  };
  if (!p.enrollment) return next;
  const days = allDays(next);
  const doneDays = days.filter((d) => d.completed_at !== null);
  const first = days.find((d) => d.completed_at === null)?.day ?? null;
  return {
    ...next,
    enrollment: {
      ...p.enrollment,
      days_done: doneDays.length,
      next_day: first,
      completed_at: first === null ? (p.enrollment.completed_at ?? now) : null,
    },
  };
}

/** The programme with a week's self-evaluation set. */
export function withRating(p: GrowthProgram, week: number, rating: number | null): GrowthProgram {
  return { ...p, weeks: p.weeks.map((w) => (w.number === week ? { ...w, rating } : w)) };
}
