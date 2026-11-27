/** Share links carry the token in the fragment, which browsers never send to the web server or in Referer. */
export function cardLink(origin: string, token: string): string {
  return `${origin}/card#token=${encodeURIComponent(token)}`;
}

/** Reads the token from "#token=…", or null if there is none. */
export function tokenFromHash(hash: string): string | null {
  const token = new URLSearchParams(hash.replace(/^#/, "")).get("token");
  return token && /^[\w-]{20,128}$/.test(token) ? token : null;
}

export const BAND_POSITION = { lower: 0, middle: 1, higher: 2 } as const;
