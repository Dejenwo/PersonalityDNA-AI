/**
 * Autosave queue for assessment answers.
 *
 * Answers are applied locally at once and sent in small batches. If a save fails (offline,
 * server error) the pending answers stay queued and are retried with backoff; newer answers
 * for the same item replace older pending ones. Only one request is in flight at a time,
 * so the server always receives answers in the order they were given.
 */

export type SaveFn = (answers: { item_id: string; value: number | null }[]) => Promise<void>;
export type QueueStatus = "idle" | "saving" | "saved" | "retrying" | "error";

export interface QueueOptions {
  debounceMs?: number;
  retryDelaysMs?: number[];
  onStatus?: (status: QueueStatus, error?: unknown) => void;
  /** Errors for which retrying cannot help (e.g. 409 session closed, 422 invalid). */
  isFatal?: (error: unknown) => boolean;
  setTimer?: (fn: () => void, ms: number) => unknown;
  clearTimer?: (handle: unknown) => void;
}

export class AnswerQueue {
  private pending = new Map<string, number | null>();
  private inFlight: Promise<void> | null = null;
  private timer: unknown = null;
  private attempt = 0;
  private readonly debounceMs: number;
  private readonly retryDelays: number[];
  private readonly setTimer: (fn: () => void, ms: number) => unknown;
  private readonly clearTimer: (handle: unknown) => void;

  constructor(
    private readonly save: SaveFn,
    private readonly opts: QueueOptions = {},
  ) {
    this.debounceMs = opts.debounceMs ?? 400;
    this.retryDelays = opts.retryDelaysMs ?? [1000, 2000, 5000, 10000];
    this.setTimer = opts.setTimer ?? ((fn, ms) => setTimeout(fn, ms));
    this.clearTimer = opts.clearTimer ?? ((h) => clearTimeout(h as ReturnType<typeof setTimeout>));
  }

  get hasPending(): boolean {
    return this.pending.size > 0 || this.inFlight !== null;
  }

  put(itemId: string, value: number | null): void {
    this.pending.set(itemId, value);
    this.attempt = 0;
    this.schedule(this.debounceMs);
  }

  /** Send everything now and resolve when nothing is pending; rejects if a save fails. */
  async flush(): Promise<void> {
    this.cancelTimer();
    while (this.pending.size > 0 || this.inFlight) {
      if (this.inFlight) {
        await this.inFlight.catch(() => undefined);
        continue;
      }
      await this.send(true);
    }
  }

  private cancelTimer() {
    if (this.timer !== null) {
      this.clearTimer(this.timer);
      this.timer = null;
    }
  }

  private schedule(ms: number) {
    this.cancelTimer();
    this.timer = this.setTimer(() => {
      this.timer = null;
      void this.send(false).catch(() => undefined);
    }, ms);
  }

  private async send(throwOnError: boolean): Promise<void> {
    if (this.inFlight || this.pending.size === 0) return;
    const batch = [...this.pending.entries()].map(([item_id, value]) => ({ item_id, value }));
    this.pending.clear();
    this.opts.onStatus?.("saving");
    const run = this.save(batch);
    this.inFlight = run;
    try {
      await run;
      this.attempt = 0;
      this.inFlight = null;
      if (this.pending.size > 0) this.schedule(0);
      else this.opts.onStatus?.("saved");
    } catch (error) {
      this.inFlight = null;
      // Put the failed batch back underneath anything newer.
      for (const { item_id, value } of batch) if (!this.pending.has(item_id)) this.pending.set(item_id, value);
      if (this.opts.isFatal?.(error)) {
        this.opts.onStatus?.("error", error);
        if (throwOnError) throw error;
        return;
      }
      const delay = this.retryDelays[Math.min(this.attempt, this.retryDelays.length - 1)] ?? 5000;
      this.attempt += 1;
      this.opts.onStatus?.("retrying", error);
      if (throwOnError) throw error;
      this.schedule(delay);
    }
  }
}
