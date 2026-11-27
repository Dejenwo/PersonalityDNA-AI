import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";
import { format, richParts, signature } from "./format";
import { REGISTRY, resolveLocale, selectableLocales } from "./locales";
import { en } from "./messages/en";
import { coverage } from "./coverage";
import { catalogueFor, lookup } from "./provider";
import { pseudoLocalize } from "./pseudo";

function leaves(node: unknown, prefix = ""): [string, string][] {
  if (typeof node === "string") return [[prefix, node]];
  return Object.entries(node as Record<string, unknown>).flatMap(([k, v]) => leaves(v, prefix ? `${prefix}.${k}` : k));
}

describe("message formatting", () => {
  it("fills placeholders and plurals", () => {
    expect(format("Hi {name}", { name: "Ada" })).toBe("Hi Ada");
    expect(format("Hi {name}")).toBe("Hi {name}");
    const m = "{count, plural, =0 {none} one {# text} other {# texts}} left";
    expect(format(m, { count: 0 })).toBe("none left");
    expect(format(m, { count: 1 })).toBe("1 text left");
    expect(format(m, { count: 1200 }, "en")).toBe("1,200 texts left");
    expect(format(m, { count: 1200 }, "de")).toBe("1.200 texts left");
  });

  it("splits tagged text", () => {
    expect(richParts("a <x>b</x> c")).toEqual([{ text: "a " }, { text: "b", tag: "x" }, { text: " c" }]);
    expect(signature("Hi {name}, <ipip>x</ipip> {count, plural, one {#} other {#}}")).toEqual([
      "<ipip>",
      "{count}",
      "{name}",
    ]);
  });
});

describe("pseudo-localisation", () => {
  it("changes text but keeps placeholders, plural keywords and tags", () => {
    const m = "Hello {name}, <ipip>read</ipip> {count, plural, one {# text} other {# texts}}";
    const p = pseudoLocalize(m);
    expect(p).not.toContain("Hello");
    expect(signature(p)).toEqual(signature(m));
    expect(p).toContain("{count, plural, one {# ţéẋţ} other {# ţéẋţš}}");
    expect(format(p, { name: "Ada", count: 2 })).toContain("2 ţéẋţš");
    expect(p.length).toBeGreaterThan(m.length);
  });
});

describe("catalogues", () => {
  it("has no empty source messages", () => {
    for (const [key, value] of leaves(en)) expect(value.trim(), key).not.toBe("");
  });

  it("every catalogue keeps the source keys and placeholders", () => {
    for (const code of ["en-XA", "ar-XB"]) {
      const cat = catalogueFor(code);
      for (const [key, value] of leaves(en)) expect(signature(lookup(cat, key)), `${code} ${key}`).toEqual(signature(value));
    }
    expect(lookup(en, "nav.missing")).toBe("nav.missing");
  });

  it("reports translation coverage", () => {
    expect(coverage("en")).toBe(1);
    expect(coverage("es")).toBe(0);
  });
});

describe("locales", () => {
  it("matches the API's registry", () => {
    const backend = JSON.parse(
      readFileSync(resolve(__dirname, "../../../../services/backend/app/i18n/locales.v1.json"), "utf8"),
    );
    expect(REGISTRY).toEqual(backend);
  });

  it("offers released languages, and pseudo-locales only in preview", () => {
    expect(selectableLocales(false).map((l) => l.code)).toEqual(["en"]);
    expect(selectableLocales(true).map((l) => l.code)).toEqual(["en", "en-XA", "ar-XB"]);
    expect(resolveLocale(null, ["es-MX", "en-GB"], false)).toBe("en");
    expect(resolveLocale("ar-XB", [], false)).toBe("en");
    expect(resolveLocale("ar-XB", [], true)).toBe("ar-XB");
    expect(resolveLocale("es", ["fr"], true)).toBe("en");
  });
});
