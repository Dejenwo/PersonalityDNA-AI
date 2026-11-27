import { describe, expect, it } from "vitest";
import { captureAttribution, clearAttribution, parseAttribution, storedAttribution } from "./attribution";

function memory() {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
  };
}

describe("attribution", () => {
  it("keeps only well-formed tags", () => {
    expect(parseAttribution("?ref=ABCD2345&utm_source=Newsletter&utm_medium=bad%20tag")).toEqual({
      referral: "abcd2345",
      source: "newsletter",
      medium: null,
      campaign: null,
    });
    expect(parseAttribution("?q=1")).toBeNull();
  });

  it("keeps the first touch for 30 days", () => {
    const store = memory();
    captureAttribution("?ref=first123", store, 0);
    captureAttribution("?ref=second12", store, 1000);
    expect(storedAttribution(store, 2000)?.referral).toBe("first123");
    expect(storedAttribution(store, 31 * 86_400_000)).toBeNull();
    captureAttribution("?utm_source=ads", store, 0);
    clearAttribution(store);
    expect(storedAttribution(store, 0)).toBeNull();
  });
});
