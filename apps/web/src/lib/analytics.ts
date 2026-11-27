import { API_URL } from "./api";

/**
 * Counts an anonymous product event (a daily total by name). Nothing identifies the person: no account,
 * cookie or page address is sent. Browsers that send Global Privacy Control or Do Not Track are not counted.
 * Failures are ignored.
 */
export type ProductEvent =
  | "landing_view"
  | "pricing_view"
  | "assessment_intro_view"
  | "big_five_article_view"
  | "referral_landing"
  | "share_card_view"
  | "organisations_view";

export function optedOut(nav: { doNotTrack?: string | null; globalPrivacyControl?: boolean } | undefined): boolean {
  return !!nav && (nav.globalPrivacyControl === true || nav.doNotTrack === "1" || nav.doNotTrack === "yes");
}

export function track(name: ProductEvent): void {
  if (typeof window === "undefined" || optedOut(window.navigator as Navigator & { globalPrivacyControl?: boolean }))
    return;
  try {
    void fetch(`${API_URL}/api/v1/analytics/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
      keepalive: true,
      credentials: "omit",
    }).catch(() => undefined);
  } catch {
    /* ignore */
  }
}
