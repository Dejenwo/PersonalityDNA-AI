import type { RelationType } from "@pdna/api-client";

export const RELATION_TYPES: { id: RelationType; label: string; other: string }[] = [
  { id: "partner", label: "Partner", other: "your partner" },
  { id: "friend", label: "Friend", other: "your friend" },
  { id: "family", label: "Family member", other: "your family member" },
  { id: "colleague", label: "Colleague", other: "your colleague" },
];

export function relationLabel(type: RelationType): string {
  return RELATION_TYPES.find((t) => t.id === type)?.label ?? type;
}

/** How to refer to the other person: their display name, or "your partner" and so on. */
export function otherName(name: string | null | undefined, type: RelationType): string {
  return name?.trim() || (RELATION_TYPES.find((t) => t.id === type)?.other ?? "the other person");
}

export function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const KEY = "pdna.invite.v1";

export interface InviteStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** Token from a `#token=` fragment, if any. */
export function tokenFromHash(hash: string): string | null {
  const token = new URLSearchParams(hash.replace(/^#/, "")).get("token");
  return token && /^[\w-]{10,256}$/.test(token) ? token : null;
}

/**
 * Reads an invitation token from the address fragment and keeps it for this tab, so it survives a
 * detour through sign-in. The fragment is never sent to servers; it is removed from the address bar.
 */
export function captureInviteToken(loc: Pick<Location, "hash" | "pathname">, store: InviteStore | null): string | null {
  const fromHash = tokenFromHash(loc.hash);
  if (fromHash) {
    try {
      store?.setItem(KEY, fromHash);
    } catch {
      /* storage blocked: the token still works for this page view */
    }
    return fromHash;
  }
  try {
    return store?.getItem(KEY) ?? null;
  } catch {
    return null;
  }
}

export function forgetInviteToken(store: InviteStore | null): void {
  try {
    store?.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

export function inviteLink(origin: string, token: string): string {
  return `${origin}/relationships/join#token=${encodeURIComponent(token)}`;
}
