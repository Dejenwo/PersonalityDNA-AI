import type { Schemas } from "@pdna/api-client";

/** First-touch attribution from the landing link, kept on this device for 30 days and sent once at sign-up. */
export type Attribution = Schemas["AttributionIn"];

const KEY = "pdna.attribution.v1";
const TTL_MS = 30 * 86_400_000;
const TAG = /^[a-z0-9][a-z0-9_.-]{0,63}$/;
const CODE = /^[a-z0-9]{4,16}$/;

export interface KeyValueStore {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/** Valid tags from a query string, or null when there are none. Values are lower-cased; others dropped. */
export function parseAttribution(search: string): Attribution | null {
  const q = new URLSearchParams(search);
  const pick = (name: string, re: RegExp) => {
    const v = q.get(name)?.trim().toLowerCase();
    return v && re.test(v) ? v : null;
  };
  const a: Attribution = {
    referral: pick("ref", CODE),
    source: pick("utm_source", TAG),
    medium: pick("utm_medium", TAG),
    campaign: pick("utm_campaign", TAG),
  };
  return Object.values(a).some(Boolean) ? a : null;
}

/** Keeps the first touch: a later link doesn't overwrite an unexpired earlier one. */
export function captureAttribution(search: string, store: KeyValueStore | null, now = Date.now()): Attribution | null {
  const found = parseAttribution(search);
  if (!found || !store) return found;
  try {
    if (!storedAttribution(store, now)) store.setItem(KEY, JSON.stringify({ at: now, ...found }));
  } catch {
    /* storage blocked */
  }
  return found;
}

export function storedAttribution(store: KeyValueStore | null, now = Date.now()): Attribution | null {
  try {
    const raw = store?.getItem(KEY);
    if (!raw) return null;
    const { at, ...a } = JSON.parse(raw) as Attribution & { at: number };
    if (typeof at !== "number" || now - at > TTL_MS) {
      store?.removeItem(KEY);
      return null;
    }
    return a;
  } catch {
    return null;
  }
}

export function clearAttribution(store: KeyValueStore | null): void {
  try {
    store?.removeItem(KEY);
  } catch {
    /* ignore */
  }
}
