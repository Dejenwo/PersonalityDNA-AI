import { en } from "./messages/en";
import { CATALOGUES } from "./catalogues";

function leaves(node: unknown, prefix = ""): [string, string][] {
  if (typeof node === "string") return [[prefix, node]];
  return Object.entries(node as Record<string, unknown>).flatMap(([k, v]) => leaves(v, prefix ? `${prefix}.${k}` : k));
}

const SOURCE = leaves(en);

/** Share of interface messages a language has its own text for (English counts as complete). */
export function coverage(code: string): number {
  if (code === "en") return 1;
  const cat = CATALOGUES[code];
  if (!cat) return 0;
  const own = new Map(leaves(cat));
  return SOURCE.filter(([k]) => (own.get(k) ?? "").trim() !== "").length / SOURCE.length;
}
