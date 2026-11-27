import { readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { describe, expect, it } from "vitest";

const SRC = join(__dirname, "..");

function files(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    return statSync(path).isDirectory() ? files(path) : /\.tsx?$/.test(name) ? [path] : [];
  });
}

describe("raw HTML", () => {
  // The CSP allows inline scripts (see next.config.ts), so raw HTML is limited to static structured data.
  it("is only used for constant JSON-LD", () => {
    const uses = files(SRC)
      .filter((f) => !f.endsWith(".test.ts") && !f.endsWith(".test.tsx"))
      .flatMap((f) =>
        readFileSync(f, "utf8")
          .split("\n")
          .filter((line) => line.includes("dangerouslySetInnerHTML") || line.includes("innerHTML"))
          .map((line) => ({ file: relative(SRC, f), line: line.trim() })),
      );
    expect(uses.map((u) => u.file).sort()).toEqual(["app/big-five/page.tsx", "app/page.tsx"]);
    for (const u of uses) {
      expect(u.line).toContain('type="application/ld+json"');
      expect(u.line).toContain("JSON.stringify(jsonLd)");
    }
  });
});
