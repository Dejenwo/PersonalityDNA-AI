import { createApiClient } from "@pdna/api-client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * The access token lives only in memory (never in storage). The refresh token is an httpOnly
 * cookie the browser sends to /api/v1/auth; AuthProvider uses it to restore sessions on load.
 */
let accessToken: string | null = null;
let refresher: (() => Promise<string | null>) | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function setRefresher(fn: (() => Promise<string | null>) | null): void {
  refresher = fn;
}

export const api = createApiClient({
  baseUrl: API_URL,
  getAccessToken: () => accessToken,
  onUnauthorized: async () => (refresher ? refresher() : null),
});

/** Must match app/security/consent.py CURRENT_POLICY_VERSION on the backend. */
export const PRIVACY_POLICY_VERSION = "2026-11-26";
