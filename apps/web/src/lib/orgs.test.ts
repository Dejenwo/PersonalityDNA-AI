import type { Org, OrgAnalytics } from "@pdna/api-client";
import { describe, expect, it } from "vitest";
import { analyticsStatus, bandShares, canManage, licenceLabel, orgInviteLink, seatsLabel } from "./orgs";

const licence = (over: Partial<Org["licence"]> = {}): Org["licence"] => ({
  licence: "pilot",
  seat_limit: 25,
  seats_used: 3,
  licensed_until: null,
  active: false,
  ...over,
});

describe("organisation helpers", () => {
  it("knows who can manage", () => {
    expect(canManage("owner")).toBe(true);
    expect(canManage("admin")).toBe(true);
    expect(canManage("member")).toBe(false);
  });

  it("puts the token in the fragment", () => {
    expect(orgInviteLink("https://x.test", "a b")).toBe("https://x.test/orgs/join#token=a%20b");
  });

  it("describes seats and licences", () => {
    expect(seatsLabel(licence())).toBe("3 of 25 seats used");
    expect(licenceLabel(licence())).toMatch(/^Pilot/);
    const now = new Date("2026-11-27T00:00:00Z");
    expect(
      licenceLabel(
        licence({
          licence: "licensed",
          active: true,
          licensed_until: "2026-11-28T00:00:00Z",
        }),
        now,
      ),
    ).toBe("Licensed: members have Premium features (1 day left)");
    expect(
      licenceLabel(
        licence({
          licence: "licensed",
          licensed_until: "2026-11-01T00:00:00Z",
        }),
        now,
      ),
    ).toMatch(/ended/);
  });

  it("rounds band shares to 100", () => {
    expect(bandShares({ lower: 1, middle: 1, higher: 1 })).toEqual({
      lower: 34,
      middle: 33,
      higher: 33,
    });
    expect(bandShares({ lower: 3, middle: 4, higher: 3 })).toEqual({
      lower: 30,
      middle: 40,
      higher: 30,
    });
    expect(bandShares({ lower: 0, middle: 0, higher: 0 })).toEqual({
      lower: 0,
      middle: 0,
      higher: 0,
    });
  });

  it("explains hidden statistics", () => {
    const base: OrgAnalytics = {
      members: 4,
      seat_limit: 25,
      min_group: 10,
      min_cell: 3,
      consenting_members: null,
      traits: [],
      programs: [],
      note: "",
    };
    expect(analyticsStatus(base)).toMatch(/at least 10/);
    const hidden = {
      ...base,
      consenting_members: 12,
      traits: [{ trait: "o", name: "Openness", bands: null }],
    };
    expect(analyticsStatus(hidden)).toMatch(/fewer than 3/);
    const shown = {
      ...hidden,
      traits: [
        {
          trait: "o",
          name: "Openness",
          bands: { lower: 3, middle: 6, higher: 3 },
        },
      ],
    };
    expect(analyticsStatus(shown)).toBeNull();
  });
});
