export type AdminTab = "overview" | "users" | "orgs" | "feedback" | "content" | "audit";

/** Which sections a set of permissions opens, in display order. */
export function tabsFor(permissions: string[]): AdminTab[] {
  const has = (p: string) => permissions.includes(p);
  const tabs: AdminTab[] = [];
  if (has("metrics.read") || has("health.read")) tabs.push("overview");
  if (has("users.read")) tabs.push("users");
  if (has("orgs.read")) tabs.push("orgs");
  if (has("feedback.read")) tabs.push("feedback");
  if (has("content.read")) tabs.push("content");
  if (has("audit.read")) tabs.push("audit");
  return tabs;
}

export const TAB_LABEL: Record<AdminTab, string> = {
  overview: "Overview",
  users: "Accounts",
  orgs: "Organisations",
  feedback: "Feedback",
  content: "Content",
  audit: "Audit log",
};

export function money(cents: number, currency = "USD", locale = "en-US"): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency }).format(cents / 100);
}

/** "admin.user_disabled" → "Admin: user disabled" for the audit list. */
export function eventLabel(type: string): string {
  const [area, ...rest] = type.split(".");
  const what = rest.join(".").replace(/[._]/g, " ");
  return what ? `${area![0]!.toUpperCase()}${area!.slice(1)}: ${what}` : type;
}
