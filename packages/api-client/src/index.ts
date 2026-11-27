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
export type InterestsOut = Schemas["InterestsOut"];
export type Methodology = Schemas["Methodology"];
export type AnswerIn = Schemas["AnswerIn"];
export type UserOut = Schemas["UserOut"];
export type AuthOut = Schemas["AuthOut"];
export type HistoryItem = Schemas["HistoryItem"];
export type CoachStatus = Schemas["CoachStatus"];
export type CoachMessage = Schemas["CoachMessageOut"];
export type ConversationSummary = Schemas["ConversationSummary"];
export type Conversation = Schemas["ConversationOut"];
export type CoachTopic = Schemas["CreateConversationIn"]["topic"];
export type RelationshipsOut = Schemas["RelationshipsOut"];
export type RelationType = Schemas["CreateInvitationIn"]["relation_type"];
export type LinkSummary = Schemas["LinkSummary"];
export type LinkDetail = Schemas["LinkDetail"];
export type TraitComparison = Schemas["TraitComparisonOut"];
export type InvitationPreview = Schemas["InvitationPreview"];
export type LeadershipOut = Schemas["LeadershipOut"];
export type ModuleList = Schemas["ModuleList"];
export type LearningModule = Schemas["ModuleOut"];
export type LearningTrack = "leadership" | "emotional-awareness";
export type ProgramList = Schemas["ProgramList"];
export type ProgramSummary = Schemas["ProgramSummary"];
export type GrowthProgram = Schemas["ProgramOut"];
export type JournalEntry = Schemas["EntryOut"];
export type JournalEntryIn = Schemas["EntryIn"];
export type JournalEntryPatch = Schemas["EntryPatch"];
export type JournalList = Schemas["EntryList"];
export type JournalSearch = Schemas["SearchIn"];
export type JournalPrompts = Schemas["PromptsOut"];
export type JournalKind = JournalEntry["kind"];
export type Goal = Schemas["GoalOut"];
export type GoalIn = Schemas["GoalIn"];
export type GoalPatch = Schemas["GoalPatch"];
export type Habit = Schemas["HabitOut"];
export type HabitIn = Schemas["HabitIn"];
export type HabitPatch = Schemas["HabitPatch"];
export type HabitList = Schemas["HabitList"];
export type Report = Schemas["ReportOut"];
export type ReportBody = Schemas["ReportBody"];
export type ReportSummary = Schemas["ReportSummary"];
export type ReportList = Schemas["ReportList"];
export type ShareCard = Schemas["ShareCardOut"];
export type PublicCard = Schemas["Card"];
export type CreateCardIn = Schemas["CreateCardIn"];
export type Plans = Schemas["PlansOut"];
export type Plan = Schemas["Plan"];
export type Billing = Schemas["BillingOut"];

/** Events streamed by POST /coach/conversations/{id}/messages (server-sent events). */
export type CoachEvent =
  | { event: "start"; data: { conversation_id: string } }
  | { event: "delta"; data: { text: string } }
  | { event: "retract"; data: { reason: string } }
  | { event: "done"; data: { user_message: CoachMessage; assistant_message: CoachMessage; remaining: number } }
  | { event: "error"; data: { code: string; message: string; retryable: boolean } };

/**
 * Incremental server-sent-events parser. Feed it decoded text as it arrives; it returns the complete
 * events so far and keeps any partial event for the next call.
 */
export function createSseParser() {
  let buffer = "";
  return (chunk: string): CoachEvent[] => {
    buffer += chunk.replace(/\r\n/g, "\n");
    const events: CoachEvent[] = [];
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      let name = "message";
      const data: string[] = [];
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) name = line.slice(6).trim();
        else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
      }
      if (data.length === 0) continue;
      try {
        events.push({ event: name, data: JSON.parse(data.join("\n")) } as CoachEvent);
      } catch {
        // Ignore malformed events rather than breaking the conversation.
      }
    }
    return events;
  };
}

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

  async function authorized(method: string, path: string, opts: RequestOptions): Promise<Response> {
    const bearer = opts.auth === false ? null : (getAccessToken?.() ?? null);
    let res = await send(method, path, opts, bearer);
    if (res.status === 401 && bearer && onUnauthorized) {
      const fresh = await onUnauthorized();
      if (fresh) res = await send(method, path, opts, fresh);
    }
    return res;
  }

  async function fail(res: Response): Promise<never> {
    const data: unknown = await res.json().catch(() => undefined);
    const err = (data as { error?: { code?: string; message?: string; details?: unknown } } | undefined)?.error;
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? `Request failed (${res.status})`, err?.details);
  }

  async function request<T>(method: string, path: string, opts: RequestOptions = {}): Promise<T> {
    const res = await authorized(method, path, opts);
    if (res.status === 204) return undefined as T;
    if (!res.ok) return fail(res);
    return (await res.json().catch(() => undefined)) as T;
  }

  async function requestText(path: string, accept: string): Promise<string> {
    const res = await authorized("GET", path, { headers: { Accept: accept } });
    if (!res.ok) return fail(res);
    return res.text();
  }

  async function requestBlob(path: string, accept: string): Promise<Blob> {
    const res = await authorized("GET", path, { headers: { Accept: accept } });
    if (!res.ok) return fail(res);
    return res.blob();
  }

  /** Sends a coach message and calls onEvent for each streamed event. Resolves when the stream ends. */
  async function streamCoachMessage(
    conversationId: string,
    content: string,
    onEvent: (e: CoachEvent) => void,
  ): Promise<void> {
    const res = await authorized("POST", `/api/v1/coach/conversations/${encodeURIComponent(conversationId)}/messages`, {
      body: { content },
      headers: { Accept: "text/event-stream" },
    });
    if (!res.ok) return fail(res);
    if (!res.body) throw new ApiError(0, "stream_unsupported", "This browser can't receive the coach's reply.");
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    const parse = createSseParser();
    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const e of parse(decoder.decode(value, { stream: true }))) onEvent(e);
      }
      for (const e of parse(decoder.decode() + "\n\n")) onEvent(e);
    } catch (err) {
      if (err instanceof ApiError) throw err;
      throw new ApiError(0, "network_error", "The connection dropped before the coach finished replying.");
    }
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

    // AI coach
    coachStatus: () => request<CoachStatus>("GET", "/api/v1/coach/status"),
    listConversations: () => request<Schemas["ConversationList"]>("GET", "/api/v1/coach/conversations"),
    createConversation: (body: Schemas["CreateConversationIn"]) =>
      request<Conversation>("POST", "/api/v1/coach/conversations", { body }),
    getConversation: (id: string) => request<Conversation>("GET", `/api/v1/coach/conversations/${seg(id)}`),
    deleteConversation: (id: string) => request<void>("DELETE", `/api/v1/coach/conversations/${seg(id)}`),
    streamCoachMessage,

    // Relationships
    relationships: () => request<RelationshipsOut>("GET", "/api/v1/relationships"),
    createInvitation: (relation_type: RelationType, policy_version: string) =>
      request<Schemas["CreatedInvitation"]>("POST", "/api/v1/relationships/invitations", {
        body: { relation_type, consent: { accepted: true, policy_version } },
      }),
    cancelInvitation: (id: string) => request<void>("DELETE", `/api/v1/relationships/invitations/${seg(id)}`),
    previewInvitation: (token: string) =>
      request<InvitationPreview>("POST", "/api/v1/relationships/invitations/preview", { body: { token } }),
    acceptInvitation: (token: string, policy_version: string) =>
      request<LinkSummary>("POST", "/api/v1/relationships/invitations/accept", {
        body: { token, consent: { accepted: true, policy_version } },
      }),
    getRelationship: (id: string) => request<LinkDetail>("GET", `/api/v1/relationships/${seg(id)}`),
    revokeRelationship: (id: string) => request<void>("DELETE", `/api/v1/relationships/${seg(id)}`),

    // Learning tracks (leadership development, emotional awareness)
    learningModules: (track: LearningTrack) => request<ModuleList>("GET", `/api/v1/learning/${seg(track)}/modules`),
    learningModule: (track: LearningTrack, id: string) =>
      request<LearningModule>("GET", `/api/v1/learning/${seg(track)}/modules/${seg(id)}`),
    setActivityDone: (track: LearningTrack, moduleId: string, activityId: string, done: boolean) =>
      request<void>(
        done ? "PUT" : "DELETE",
        `/api/v1/learning/${seg(track)}/modules/${seg(moduleId)}/activities/${seg(activityId)}/done`,
      ),

    // Personal growth academy
    growthPrograms: () => request<ProgramList>("GET", "/api/v1/growth/programs"),
    growthProgram: (id: string) => request<GrowthProgram>("GET", `/api/v1/growth/programs/${seg(id)}`),
    startProgram: (id: string) => request<GrowthProgram>("POST", `/api/v1/growth/programs/${seg(id)}/enrollment`),
    leaveProgram: (id: string) => request<void>("DELETE", `/api/v1/growth/programs/${seg(id)}/enrollment`),
    setDayDone: (id: string, day: number, done: boolean) =>
      request<void>(done ? "PUT" : "DELETE", `/api/v1/growth/programs/${seg(id)}/days/${day}/done`),
    setCheckIn: (id: string, week: number, rating: number) =>
      request<void>("PUT", `/api/v1/growth/programs/${seg(id)}/weeks/${week}/check-in`, { body: { rating } }),

    // Private journal. Search is a POST so the words never appear in URLs or server logs.
    journalPrompts: () => request<JournalPrompts>("GET", "/api/v1/journal/prompts", { auth: false }),
    journalEntries: (cursor?: string | null) =>
      request<JournalList>("GET", `/api/v1/journal/entries${cursor ? `?cursor=${encodeURIComponent(cursor)}` : ""}`),
    journalSearch: (body: Partial<JournalSearch>) => request<JournalList>("POST", "/api/v1/journal/search", { body }),
    journalEntry: (id: string) => request<JournalEntry>("GET", `/api/v1/journal/entries/${seg(id)}`),
    createJournalEntry: (body: JournalEntryIn) => request<JournalEntry>("POST", "/api/v1/journal/entries", { body }),
    updateJournalEntry: (id: string, body: JournalEntryPatch) =>
      request<JournalEntry>("PATCH", `/api/v1/journal/entries/${seg(id)}`, { body }),
    deleteJournalEntry: (id: string) => request<void>("DELETE", `/api/v1/journal/entries/${seg(id)}`),
    deleteAllJournalEntries: () => request<void>("POST", "/api/v1/journal/delete-all", { body: { confirm: true } }),
    journalTags: () => request<Schemas["TagsOut"]>("GET", "/api/v1/journal/tags"),
    // Goals, milestones and habits. `today` is the person's local date (YYYY-MM-DD).
    goals: () => request<Schemas["GoalList"]>("GET", "/api/v1/goals"),
    goal: (id: string) => request<Goal>("GET", `/api/v1/goals/${seg(id)}`),
    createGoal: (body: GoalIn) => request<Goal>("POST", "/api/v1/goals", { body }),
    updateGoal: (id: string, body: GoalPatch) => request<Goal>("PATCH", `/api/v1/goals/${seg(id)}`, { body }),
    deleteGoal: (id: string) => request<void>("DELETE", `/api/v1/goals/${seg(id)}`),
    addMilestone: (goalId: string, title: string, due_date: string | null = null) =>
      request<Goal>("POST", `/api/v1/goals/${seg(goalId)}/milestones`, { body: { title, due_date } }),
    updateMilestone: (goalId: string, id: string, body: Schemas["MilestonePatch"]) =>
      request<Goal>("PATCH", `/api/v1/goals/${seg(goalId)}/milestones/${seg(id)}`, { body }),
    deleteMilestone: (goalId: string, id: string) =>
      request<Goal>("DELETE", `/api/v1/goals/${seg(goalId)}/milestones/${seg(id)}`),
    habits: (today: string) => request<HabitList>("GET", `/api/v1/habits?today=${seg(today)}`),
    createHabit: (body: HabitIn, today: string) =>
      request<Habit>("POST", `/api/v1/habits?today=${seg(today)}`, { body }),
    updateHabit: (id: string, body: HabitPatch, today: string) =>
      request<Habit>("PATCH", `/api/v1/habits/${seg(id)}?today=${seg(today)}`, { body }),
    deleteHabit: (id: string) => request<void>("DELETE", `/api/v1/habits/${seg(id)}`),
    setHabitDone: (id: string, day: string, done: boolean, today: string) =>
      request<Habit>(done ? "PUT" : "DELETE", `/api/v1/habits/${seg(id)}/checks/${seg(day)}?today=${seg(today)}`),

    exportJournal: (format: "markdown" | "json") =>
      requestText(`/api/v1/journal/export?format=${format}`, format === "json" ? "application/json" : "text/markdown"),

    reports: () => request<ReportList>("GET", "/api/v1/reports"),
    report: (id: string) => request<Report>("GET", `/api/v1/reports/${seg(id)}`),
    createReport: () => request<Report>("POST", "/api/v1/reports"),
    deleteReport: (id: string) => request<void>("DELETE", `/api/v1/reports/${seg(id)}`),
    reportPdf: (id: string) => requestBlob(`/api/v1/reports/${seg(id)}/pdf`, "application/pdf"),
    shareCards: () => request<{ cards: ShareCard[] }>("GET", "/api/v1/share-cards"),
    createShareCard: (body: CreateCardIn) => request<ShareCard>("POST", "/api/v1/share-cards", { body }),
    revokeShareCard: (id: string) => request<void>("DELETE", `/api/v1/share-cards/${seg(id)}`),
    publicCard: (token: string) => request<PublicCard>("GET", `/api/v1/public/cards/${seg(token)}`, { auth: false }),
    plans: () => request<Plans>("GET", "/api/v1/billing/plans", { auth: false }),
    billing: () => request<Billing>("GET", "/api/v1/billing/me"),
    checkout: (planId: string) =>
      request<{ url: string }>("POST", "/api/v1/billing/checkout", { body: { plan_id: planId } }),
    manageSubscription: () => request<{ url: string }>("POST", "/api/v1/billing/manage"),
    publicCardImageUrl: (token: string) => `${root}/api/v1/public/cards/${seg(token)}/image.svg`,
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
