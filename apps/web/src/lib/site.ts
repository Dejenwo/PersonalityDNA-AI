/** Public address of the web app, used for canonical links, the sitemap and social previews. */
export const SITE_URL = (process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000").replace(/\/+$/, "");

export const SITE_NAME = "PersonalityDNA AI";

/** Pages search engines may index. Everything signed-in, shared or tokenised stays out. */
export const PUBLIC_PATHS = ["/", "/discover", "/big-five", "/learn", "/careers", "/pricing", "/privacy"] as const;

/** Prefixes kept out of search results (robots.txt). Tokens live in fragments, but the pages are private. */
export const PRIVATE_PREFIXES = [
  "/account",
  "/admin",
  "/assessment/",
  "/card",
  "/coach",
  "/goals",
  "/history",
  "/journal",
  "/notifications",
  "/orgs",
  "/relationships",
  "/reports",
  "/reset-password",
  "/results",
  "/verify-email",
] as const;
