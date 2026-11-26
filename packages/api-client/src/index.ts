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
}

export function createApiClient({ baseUrl, fetch: f = globalThis.fetch.bind(globalThis) }: ClientOptions) {
  const root = baseUrl.replace(/\/$/, "");

  async function request<T>(method: string, path: string, opts: { token?: string; body?: unknown } = {}): Promise<T> {
    const headers: Record<string, string> = { Accept: "application/json" };
    if (opts.body !== undefined) headers["Content-Type"] = "application/json";
    if (opts.token) headers["X-Session-Token"] = opts.token;
    let res: Response;
    try {
      res = await f(`${root}${path}`, {
        method,
        headers,
        body: opts.body === undefined ? undefined : JSON.stringify(opts.body),
        cache: "no-store",
      });
    } catch {
      throw new ApiError(0, "network_error", "We couldn't reach PersonalityDNA. Check your connection and try again.");
    }
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
    getSession: (id: string, token: string) =>
      request<SessionOut>("GET", `/api/v1/assessment-sessions/${seg(id)}`, { token }),
    saveAnswers: (id: string, token: string, answers: AnswerIn[]) =>
      request<SaveAnswersOut>("PUT", `/api/v1/assessment-sessions/${seg(id)}/answers`, { token, body: { answers } }),
    completeSession: (id: string, token: string) =>
      request<ResultOut>("POST", `/api/v1/assessment-sessions/${seg(id)}/complete`, { token }),
    getResult: (id: string, token: string) => request<ResultOut>("GET", `/api/v1/results/${seg(id)}`, { token }),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
