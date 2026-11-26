import { describe, expect, it } from "vitest";
import { captureInviteToken, forgetInviteToken, inviteLink, otherName, tokenFromHash } from "./relationships";

function memory() {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k),
  };
}

const TOKEN = "abcDEF123_-xyz789";

describe("invite tokens", () => {
  it("parses only well-formed tokens from the fragment", () => {
    expect(tokenFromHash(`#token=${TOKEN}`)).toBe(TOKEN);
    expect(tokenFromHash("#token=short")).toBeNull();
    expect(tokenFromHash("#token=<script>alert(1)</script>")).toBeNull();
    expect(tokenFromHash("")).toBeNull();
  });

  it("keeps the token across a sign-in detour, then forgets it", () => {
    const store = memory();
    expect(captureInviteToken({ hash: `#token=${TOKEN}`, pathname: "/relationships/join" }, store)).toBe(TOKEN);
    expect(captureInviteToken({ hash: "", pathname: "/relationships/join" }, store)).toBe(TOKEN);
    forgetInviteToken(store);
    expect(captureInviteToken({ hash: "", pathname: "/relationships/join" }, store)).toBeNull();
  });

  it("works without storage", () => {
    expect(captureInviteToken({ hash: `#token=${TOKEN}`, pathname: "/" }, null)).toBe(TOKEN);
    expect(captureInviteToken({ hash: "", pathname: "/" }, null)).toBeNull();
  });

  it("builds links with the token in the fragment", () => {
    expect(inviteLink("https://app.example", TOKEN)).toBe(`https://app.example/relationships/join#token=${TOKEN}`);
  });
});

describe("otherName", () => {
  it("prefers the display name and falls back to the relation", () => {
    expect(otherName("Ada", "partner")).toBe("Ada");
    expect(otherName("  ", "friend")).toBe("your friend");
    expect(otherName(null, "colleague")).toBe("your colleague");
  });
});
