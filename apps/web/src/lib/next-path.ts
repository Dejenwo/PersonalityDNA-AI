/** Where to go after signing in. Only same-site paths are allowed, to prevent open redirects. */
export function safeNextPath(search: string, fallback = "/history"): string {
  const next = new URLSearchParams(search).get("next");
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return fallback;
  return next;
}
