/**
 * Typed client for the PersonalityDNA API. Types are generated from the backend's OpenAPI
 * document (src/schema.d.ts, via `pnpm api:generate`); never edit them by hand.
 */
import type { components } from "./schema";

export type Schemas = components["schemas"];
export type AssessmentSummary = Schemas["AssessmentSummary"];
export type AssessmentDetail = Schemas["AssessmentDetail"];
export type SessionOut = Schemas["SessionOut"];
export type CreateSessionOut = Schemas["CreateSessionOut"];
export type SaveAnswersOut = Schemas["SaveAnswersOut"];
export type ResultOut = Schemas["ResultOut"];
export type TraitResult = Schemas["TraitResult"];
export type ArchetypeOut = Schemas["ArchetypeOut"];
export type AnswerIn = Schemas["AnswerIn"];
export type UserOut = Schemas["UserOut"];
export type AuthOut = Schemas["AuthOut"];
export type HistoryItem = Schemas["HistoryItem"];

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export interface ClientOptions {
  baseUrl: string;
  fetch?: typeof fetch;
  /** Current access token, if signed in. */
  getAccessToken?: () => string | null;
  /** Called once when a signed-in request gets 401; return a fresh token to retry, or null. */
  onUnauthorized?: () => Promise<string | null>;
}

interface RequestOptions {
  token?: string;
  body?: unknown;
  /** Send the bearer token if available (default true). */
  auth?: boolean;
  headers?: Record<string, string>;
}

export function createApiClient({
  baseUrl,
  fetch: f = globalThis.fetch.bind(globalThis),
  getAccessToken,
  onUnauthorized,
}: ClientOptions) {
  const root = baseUrl.replace(/\/$/, "");

  async function send(method: string, path: string, opts: RequestOptions, bearer: string | null): Promise<Response> {
    const headers: Record<string, string> = { Accept: "application/json", ...opts.headers };
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (opts.token) headers["X-Session-Token"] = opts.token;
    if (bearer) headers.Authorization = `Bearer ${bearer}`;
    try {
      return await f(`${root}${path}`, {
        method,
        headers,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        cache: "no-store",
        credentials: "include",
      });
    } catch {
      throw new ApiError(0, "network_error", "We couldn't reach PersonalityDNA. Check your connection and try again.");
    }
  }

  async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
    const bearer = opts.auth === false ? null : (getAccessToken?.() ?? null);
    let res = await send(method, path, opts, bearer);
    if (res.status === 401 && bearer && onUnauthorized) {
      const fresh = await onUnauthorized();
      if (fresh) res = await send(method, path, opts, fresh);
    }
    if (res.status === 204) return undefined as T;
    const data: unknown = await res.json().catch(() => undefined);
    if (!res.ok) {
      const err = (data as { error?: { code?: string; message?: string; details?: unknown } } | undefined)?.error;
      throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? `Request failed (${res.status})`, err?.details);
    }
    return data as T;
  }

  const seg = encodeURIComponent;
  return {
    listAssessments: () => request<Schemas["AssessmentList"]>("GET", "/api/v1/assessments"),
    getAssessment: (id: string) => request<AssessmentDetail>("GET", `/api/v1/assessments/${seg(id)}`),
    createSession: (body: Schemas["CreateSessionIn"]) =>
      request<CreateSessionOut>("POST", "/api/v1/assessment-sessions", { body }),
    getSession: (id: string, token?: string) =>
      request<SessionOut>("GET", `/api/v1/assessment-sessions/${seg(id)}`, { token }),
    saveAnswers: (id: string, token: string | undefined, answers: AnswerIn[]) =>
      request<SaveAnswersOut>("PUT", `/api/v1/assessment-sessions/${seg(id)}/answers`, { token, body: { answers } }),
    completeSession: (id: string, token?: string) =>
      request<ResultOut>("POST", `/api/v1/assessment-sessions/${seg(id)}/complete`, { token }),
    getResult: (id: string, token?: string) => request<ResultOut>("GET", `/api/v1/results/${seg(id)}`, { token }),

    // Accounts
    register: (body: Schemas["RegisterIn"]) =>
      request<Schemas["MessageOut"]>("POST", "/api/v1/auth/register", { body, auth: false }),
    verifyEmail: (token: string) =>
      request<UserOut>("POST", "/api/v1/auth/verify-email", { body: { token }, auth: false }),
    resendVerification: (email: string) =>
      request<Schemas["MessageOut"]>("POST", "/api/v1/auth/resend-verification", { body: { email }, auth: false }),
    login: (email: string, password: string) =>
      request<AuthOut>("POST", "/api/v1/auth/login", { body: { email, password, client: "web" }, auth: false }),
    /** Uses the httpOnly refresh cookie. The custom header is required by the server (CSRF defence). */
    refresh: () =>
      request<AuthOut>("POST", "/api/v1/auth/refresh", { auth: false, headers: { "X-PDNA-CSRF": "1" } }),
    logout: () => request<void>("POST", "/api/v1/auth/logout", { auth: false }),
    requestPasswordReset: (email: string) =>
      request<Schemas["MessageOut"]>("POST", "/api/v1/auth/password-reset/request", { body: { email }, auth: false }),
    confirmPasswordReset: (token: string, password: string) =>
      request<void>("POST", "/api/v1/auth/password-reset/confirm", { body: { token, password }, auth: false }),
    me: () => request<UserOut>("GET", "/api/v1/auth/me"),
    updateMe: (body: Schemas["UpdateMeIn"]) => request<UserOut>("PATCH", "/api/v1/me", { body }),
    claimSession: (sessionId: string, resumeToken: string) =>
      request<SessionOut>("POST", "/api/v1/me/assessment-sessions/claim", {
        body: { session_id: sessionId, resume_token: resumeToken },
      }),
    history: () => request<Schemas["HistoryOut"]>("GET", "/api/v1/personality/history"),
    exportData: () => request<Record<string, unknown>>("GET", "/api/v1/privacy/export"),
    deleteAccount: (password: string) => request<void>("DELETE", "/api/v1/account", { body: { password } }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
