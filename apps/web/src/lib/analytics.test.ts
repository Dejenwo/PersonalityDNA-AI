import { describe, expect, it } from "vitest";
import { optedOut } from "./analytics";
import { PRIVATE_PREFIXES, PUBLIC_PATHS } from "./site";

describe("optedOut", () => {
  it("honours Global Privacy Control and Do Not Track", () => {
    expect(optedOut({ globalPrivacyControl: true })).toBe(true);
    expect(optedOut({ doNotTrack: "1" })).toBe(true);
    expect(optedOut({ doNotTrack: "yes" })).toBe(true);
    expect(optedOut({ doNotTrack: "0", globalPrivacyControl: false })).toBe(false);
    expect(optedOut({})).toBe(false);
    expect(optedOut(undefined)).toBe(false);
  });
});

describe("site paths", () => {
  it("never lists a private page in the sitemap", () => {
    for (const path of PUBLIC_PATHS) {
      expect(PRIVATE_PREFIXES.some((prefix) => path.startsWith(prefix))).toBe(false);
    }
  });
});
