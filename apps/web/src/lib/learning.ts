import type { CoachTopic, LearningTrack } from "@pdna/api-client";

/** Where each learning track lives in the app, and which coach topic fits it. */
export const TRACKS: Record<LearningTrack, { path: string; label: string; coachTopic: CoachTopic }> = {
  leadership: { path: "/leadership", label: "Leadership", coachTopic: "leadership" },
  "emotional-awareness": { path: "/emotional-awareness", label: "Emotional awareness", coachTopic: "emotions" },
};

export function modulePath(track: LearningTrack, moduleId: string): string {
  return `${TRACKS[track].path}/${encodeURIComponent(moduleId)}`;
}
