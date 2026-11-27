/**
 * Helpers for the career exploration page: picking the newest result of each assessment family,
 * and reflection questions about working style. The questions are prompts for the person to think
 * about, not predictions: personality scores never say which job someone should do.
 */

export type Family = "big_five" | "interests" | "leadership";

export interface ResultRef {
  instrumentId: string;
  resultId: string;
  /** ISO time used to pick the newest result. */
  at: string;
  /** Resume token for results kept on this device; absent for account results. */
  token?: string;
}

/** Newest result of each family. Instruments not in `families` (retired or unknown) are ignored. */
export function latestByFamily(refs: ResultRef[], families: Record<string, string>): Partial<Record<Family, ResultRef>> {
  const out: Partial<Record<Family, ResultRef>> = {};
  for (const ref of refs) {
    const family = families[ref.instrumentId];
    if (family !== "big_five" && family !== "interests" && family !== "leadership") continue;
    const current = out[family];
    if (!current || ref.at > current.at) out[family] = ref;
  }
  return out;
}

type Band = "lower" | "middle" | "higher";

const REFLECTIONS: Record<string, Partial<Record<Band, string>>> = {
  openness: {
    higher: "How much room for new ideas and variety would you want in a working week?",
    lower: "Which familiar, proven ways of working would you most like to build on?",
  },
  conscientiousness: {
    higher: "Where would clear plans, standards and follow-through be valued in the work you are exploring?",
    lower: "How much flexibility and freedom from fixed routines would help you do your best work?",
  },
  extraversion: {
    higher: "How much contact with other people would keep you energised during a working day?",
    lower: "How much quiet, focused time would you want, and how would you protect it?",
  },
  agreeableness: {
    higher: "Where could your care for cooperation and other people's needs make a difference?",
    lower: "Where would direct debate and frank feedback be welcome rather than avoided?",
  },
  emotional_stability: {
    higher: "Which kinds of pressure or uncertainty do you find you can take in your stride?",
    lower: "What support, pace or setting would help you feel steady when work gets demanding?",
  },
};

/** One reflection question per trait in the higher or lower band. Middle bands and unscored traits get none. */
export function workingStyleQuestions(traits: { trait: string; band: string | null }[]): string[] {
  return traits.flatMap((t) => {
    const q = t.band === "higher" || t.band === "lower" ? REFLECTIONS[t.trait]?.[t.band] : undefined;
    return q ? [q] : [];
  });
}
