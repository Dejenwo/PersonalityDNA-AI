import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { dark, light, type ThemeColors } from "./index.ts";

const css = readFileSync(new URL("./tokens.css", import.meta.url), "utf8");
const kebab = (k: string) => k.replace(/[A-Z]/g, (m) => `-${m.toLowerCase()}`);

function block(source: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const m of source.matchAll(/--pdna-([a-z-]+):\s*(#[0-9a-f]{6})/g)) out[m[1]!] = m[2]!;
  return out;
}

const darkStart = css.indexOf("@media (prefers-color-scheme: dark)");
const lightVars = block(css.slice(0, darkStart));
const darkVars = block(css.slice(darkStart));

for (const [name, theme, vars] of [
  ["light", light, lightVars],
  ["dark", dark, darkVars],
] as const) {
  test(`tokens.css ${name} values match index.ts`, () => {
    for (const [key, value] of Object.entries(theme as ThemeColors)) {
      assert.equal(vars[kebab(key)], value, `--pdna-${kebab(key)}`);
    }
  });
}
