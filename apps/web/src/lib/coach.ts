import type { CoachTopic } from "@pdna/api-client";

export const COACH_TOPICS: { id: CoachTopic; label: string; hint: string }[] = [
  { id: "results", label: "Understanding my results", hint: "What your scores describe and how they show up day to day" },
  { id: "communication", label: "Communication", hint: "Speaking up, listening and giving feedback" },
  { id: "relationships", label: "Relationships", hint: "Your side of everyday conversations and conflicts" },
  { id: "career", label: "Career exploration", hint: "Interests, working preferences and learning" },
  { id: "leadership", label: "Leadership", hint: "Leading, delegating and supporting others" },
  { id: "emotions", label: "Emotions and communication", hint: "Noticing feelings, listening and speaking up" },
  { id: "goals", label: "Goals and habits", hint: "One small goal and a habit that fits you" },
  { id: "general", label: "Something else", hint: "Any everyday personal-development question" },
];

export function limitMessage(details: unknown): string {
  const resets = (details as { resets_at?: string | null } | undefined)?.resets_at;
  if (!resets) return "You've reached today's coaching limit. Please come back later.";
  const time = new Date(resets).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" });
  return `You've reached today's coaching limit. You can send another message from ${time}.`;
}
