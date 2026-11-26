import { createApiClient } from "@pdna/api-client";

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
export const api = createApiClient({ baseUrl: API_URL });

/** Must match app/security/consent.py CURRENT_POLICY_VERSION on the backend. */
export const PRIVACY_POLICY_VERSION = "2026-11-26";
