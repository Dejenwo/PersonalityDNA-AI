import { describe, expect, it } from "vitest";
import { findByResult, findSession, forgetSession, readSessions, saveSession, updateSession } from "./session-store";

function memory() {
  const m = new Map<string, string>();
  return { getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v), m };
}

const s = (id: string) => ({
  sessionId: id,
  token: `t-${id}`,
  instrumentId: "mini-ipip-20",
  instrumentName: "Quick",
  startedAt: "2026-11-26T00:00:00Z",
});

describe("session store", () => {
  it("saves newest first, updates and forgets", () => {
    const store = memory();
    saveSession(s("1"), store);
    saveSession(s("2"), store);
    expect(readSessions(store).map((x) => x.sessionId)).toEqual(["2", "1"]);
    updateSession("1", { resultId: "r1" }, store);
    expect(findByResult("r1", store)?.sessionId).toBe("1");
    forgetSession("2", store);
    expect(findSession("2", store)).toBeUndefined();
  });

  it("survives corrupt or unavailable storage", () => {
    const store = memory();
    store.m.set("pdna.sessions.v1", "{not json");
    expect(readSessions(store)).toEqual([]);
    store.m.set("pdna.sessions.v1", JSON.stringify([{ bad: true }, s("ok")]));
    expect(readSessions(store).map((x) => x.sessionId)).toEqual(["ok"]);
    expect(readSessions(null)).toEqual([]);
    const throwing = {
      getItem: () => null,
      setItem: () => {
        throw new Error("quota");
      },
    };
    expect(saveSession(s("x"), throwing)).toBe(false);
  });
});
