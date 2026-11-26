import assert from "node:assert/strict";
import { test } from "node:test";
import { contrastPairs, dark, light } from "./index.ts";

function luminance(hex: string): number {
  const n = parseInt(hex.slice(1), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((v) => {
    const c = v / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * ch[0]! + 0.7152 * ch[1]! + 0.0722 * ch[2]!;
}

export function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

for (const [name, theme] of [["light", light], ["dark", dark]] as const) {
  test(`${name} theme meets WCAG AA 4.5:1 for text pairs`, () => {
    for (const [label, fg, bg] of contrastPairs(theme)) {
      const ratio = contrast(fg, bg);
      assert.ok(ratio >= 4.5, `${name}: ${label} is ${ratio.toFixed(2)}:1`);
    }
  });
}
