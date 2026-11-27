import { downloadBlob } from "./download";

/** Splits a comma-separated tag field into clean tags (the server normalises them again). */
export function parseTags(text: string): string[] {
  const out: string[] = [];
  for (const raw of text.split(",")) {
    const tag = raw.trim().replace(/^#+/, "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
    if (tag && !out.includes(tag)) out.push(tag);
  }
  return out;
}

/** Today's date in the person's own time zone, as YYYY-MM-DD. */
export function localToday(now: Date = new Date()): string {
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

/** "Tuesday, 3 March 2026" (style depends on the browser) for a YYYY-MM-DD date, without time zone shifts. */
export function formatEntryDate(iso: string, locale = "en-GB"): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(Date.UTC(y!, m! - 1, d!)).toLocaleDateString(locale, {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/** A short preview of an entry's text for lists. */
export function preview(text: string, max = 160): string {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length <= max ? flat : `${flat.slice(0, max - 1).trimEnd()}…`;
}

/** Saves text as a file in the browser. */
export function downloadText(text: string, filename: string, type: string): void {
  downloadBlob(new Blob([text], { type }), filename);
}
