import { describe, expect, it } from "vitest";
import { eventLabel, money, tabsFor } from "./admin";

describe("admin helpers", () => {
  it("opens only the sections a role allows", () => {
    expect(tabsFor(["metrics.read", "health.read"])).toEqual(["overview"]);
    expect(tabsFor(["users.read", "users.manage", "health.read"])).toEqual(["overview", "users"]);
    expect(tabsFor(["audit.read", "users.read", "content.read", "metrics.read"])).toEqual([
      "overview",
      "users",
      "content",
      "audit",
    ]);
    expect(tabsFor(["users.read", "orgs.read"])).toEqual(["users", "orgs"]);
    expect(tabsFor(["content.read", "feedback.read"])).toEqual(["feedback", "content"]);
    expect(tabsFor([])).toEqual([]);
  });

  it("formats money and events", () => {
    expect(money(124950)).toBe("$1,249.50");
    expect(eventLabel("admin.user_disabled")).toBe("Admin: user disabled");
    expect(eventLabel("login")).toBe("login");
  });
});
