import type { Org, OrgAnalytics, OrgRole } from "@pdna/api-client";

/** sessionStorage key for an organisation join link, kept separate from relationship invitations. */
export const ORG_INVITE_KEY = "pdna.org-invite.v1";

export const ROLE_LABEL: Record<OrgRole, string> = {
  owner: "Owner",
  admin: "Administrator",
  member: "Member",
};

type Bands = { lower: number; middle: number; higher: number };

export function canManage(role: OrgRole): boolean {
  return role === "owner" || role === "admin";
}

export function orgInviteLink(origin: string, token: string): string {
  return `${origin}/orgs/join#token=${encodeURIComponent(token)}`;
}

export function seatsLabel(licence: Org["licence"]): string {
  return `${licence.seats_used} of ${licence.seat_limit} seats used`;
}

export function licenceLabel(licence: Org["licence"], now: Date = new Date()): string {
  if (licence.active && licence.licensed_until) {
    const until = new Date(licence.licensed_until);
    const days = Math.max(0, Math.ceil((until.getTime() - now.getTime()) / 86_400_000));
    return `Licensed: members have Premium features (${days} day${days === 1 ? "" : "s"} left)`;
  }
  if (licence.licence === "licensed") return "Licence ended: members are back on their own plans";
  return "Pilot: up to the seat limit, members keep their own plans";
}

/** Whole-number percentage of each band, adding up to 100 (largest remainder). */
export function bandShares(bands: Bands): Bands {
  const keys = ["lower", "middle", "higher"] as const;
  const total = keys.reduce((n, k) => n + bands[k], 0);
  if (total === 0) return { lower: 0, middle: 0, higher: 0 };
  const out: Bands = { lower: 0, middle: 0, higher: 0 };
  const rest = keys.map((k) => {
    const raw = (bands[k] / total) * 100;
    out[k] = Math.floor(raw);
    return { k, remainder: raw - out[k] };
  });
  let left = 100 - keys.reduce((n, k) => n + out[k], 0);
  for (const { k } of rest.sort((a, b) => b.remainder - a.remainder)) {
    if (left <= 0) break;
    out[k] += 1;
    left -= 1;
  }
  return out;
}

/** Why group statistics aren't showing yet, or null when they are. */
export function analyticsStatus(a: OrgAnalytics): string | null {
  if (a.consenting_members === null)
    return `Group statistics appear once at least ${a.min_group} members have chosen to share and have a Big Five result.`;
  if (a.traits.every((t) => t.bands === null))
    return `Every trait is hidden because at least one band has fewer than ${a.min_cell} people.`;
  return null;
}
