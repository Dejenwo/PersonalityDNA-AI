import { describe, expect, it } from "vitest";
import { AnswerQueue, type QueueStatus } from "./answer-queue";

function manualTimers() {
  const timers: { fn: () => void; ms: number; id: number }[] = [];
  let next = 0;
  return {
    timers,
    setTimer: (fn: () => void, ms: number) => {
      const id = next++;
      timers.push({ fn, ms, id });
      return id;
    },
    clearTimer: (h: unknown) => {
      const i = timers.findIndex((t) => t.id === h);
      if (i >= 0) timers.splice(i, 1);
    },
    async fire() {
      const t = timers.shift();
      t?.fn();
      await new Promise((r) => setTimeout(r, 0));
      return t;
    },
  };
}

describe("AnswerQueue", () => {
  it("debounces and batches, keeping the latest value per item", async () => {
    const sent: unknown[] = [];
    const t = manualTimers();
    const q = new AnswerQueue(async (a) => void sent.push(a), t);
    q.put("a", 1);
    q.put("b", 2);
    q.put("a", 5);
    expect(t.timers).toHaveLength(1);
    await t.fire();
    expect(sent).toEqual([[{ item_id: "a", value: 5 }, { item_id: "b", value: 2 }]]);
    expect(q.hasPending).toBe(false);
  });

  it("retries failures with backoff and does not lose newer answers", async () => {
    const statuses: QueueStatus[] = [];
    const sent: unknown[] = [];
    let fail = true;
    const t = manualTimers();
    const q = new AnswerQueue(
      async (a) => {
        if (fail) throw new Error("offline");
        sent.push(a);
      },
      { ...t, retryDelaysMs: [100, 200], onStatus: (s) => statuses.push(s) },
    );
    q.put("a", 1);
    await t.fire(); // fails
    expect(statuses).toEqual(["saving", "retrying"]);
    expect(t.timers[0]?.ms).toBe(100);
    q.put("b", 3); // newer answer while waiting resets the debounce
    fail = false;
    await t.fire();
    expect(sent).toEqual([[{ item_id: "a", value: 1 }, { item_id: "b", value: 3 }]]);
    expect(statuses.at(-1)).toBe("saved");
  });

  it("newer value wins over a failed older value for the same item", async () => {
    const sent: unknown[] = [];
    let fail = true;
    const t = manualTimers();
    const q = new AnswerQueue(async (a) => {
      if (fail) throw new Error("x");
      sent.push(a);
    }, t);
    q.put("a", 1);
    await t.fire();
    q.put("a", 4);
    fail = false;
    await q.flush();
    expect(sent).toEqual([[{ item_id: "a", value: 4 }]]);
  });

  it("flush rejects on fatal errors and reports error status", async () => {
    const statuses: QueueStatus[] = [];
    const q = new AnswerQueue(
      async () => {
        throw new Error("closed");
      },
      { isFatal: () => true, onStatus: (s) => statuses.push(s), ...manualTimers() },
    );
    q.put("a", 1);
    await expect(q.flush()).rejects.toThrow("closed");
    expect(statuses).toEqual(["saving", "error"]);
  });

  it("sends one request at a time in order", async () => {
    const order: string[] = [];
    let release!: () => void;
    const t = manualTimers();
    const q = new AnswerQueue(async (a) => {
      order.push(a.map((x) => x.item_id).join(","));
      if (order.length === 1) await new Promise<void>((r) => (release = r));
    }, t);
    q.put("a", 1);
    await t.fire();
    q.put("b", 2);
    const flushed = q.flush();
    await new Promise((r) => setTimeout(r, 0));
    expect(order).toEqual(["a"]);
    release();
    await flushed;
    expect(order).toEqual(["a", "b"]);
  });
});
