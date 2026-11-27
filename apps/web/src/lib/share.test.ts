import { describe, expect, it } from "vitest";
import { cardLink, tokenFromHash } from "./share";

describe("share links", () => {
  const token = "abcDEF123_-abcDEF123_-abcDEF123_-abcDEF12";
  it("puts the token in the fragment and reads it back", () => {
    const link = cardLink("https://example.com", token);
    expect(link).toBe(`https://example.com/card#token=${token}`);
    expect(tokenFromHash(new URL(link).hash)).toBe(token);
  });

  it("ignores missing or malformed tokens", () => {
    expect(tokenFromHash("")).toBeNull();
    expect(tokenFromHash("#token=short")).toBeNull();
    expect(tokenFromHash("#token=has%20space%20in%20it%20and%20more")).toBeNull();
  });
});
