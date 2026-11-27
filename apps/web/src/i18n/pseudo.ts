/**
 * Pseudo-localisation for testing: accented, about 35% longer text (and right-to-left for the bidi variant)
 * shows hard-coded strings, truncation and layout problems without anyone writing a real translation.
 * Placeholders, plural syntax and tags are left untouched.
 */
const MAP: Record<string, string> = {
  a: "á", b: "ƀ", c: "ç", d: "ð", e: "é", f: "ƒ", g: "ĝ", h: "ĥ", i: "í", j: "ĵ", k: "ķ", l: "ľ", m: "ɱ",
  n: "ñ", o: "ó", p: "þ", q: "ǫ", r: "ŕ", s: "š", t: "ţ", u: "ú", v: "ṽ", w: "ŵ", x: "ẋ", y: "ý", z: "ž",
  A: "Á", B: "Ɓ", C: "Ç", D: "Ð", E: "É", F: "Ƒ", G: "Ĝ", H: "Ĥ", I: "Í", J: "Ĵ", K: "Ķ", L: "Ľ", M: "Ṁ",
  N: "Ñ", O: "Ó", P: "Þ", Q: "Ǫ", R: "Ŕ", S: "Š", T: "Ţ", U: "Ú", V: "Ṽ", W: "Ŵ", X: "Ẋ", Y: "Ý", Z: "Ž",
};

function closeOf(s: string, open: number): number {
  let depth = 0;
  for (let i = open; i < s.length; i++) {
    if (s[i] === "{") depth++;
    else if (s[i] === "}" && --depth === 0) return i;
  }
  return s.length - 1;
}

function accent(text: string): string {
  // Keep tags like <ipip> and </ipip> intact.
  return text.replace(/<\/?[a-z]\w*>|[^<]+/g, (part) => (part.startsWith("<") ? part : [...part].map((c) => MAP[c] ?? c).join("")));
}

function walk(message: string): string {
  let out = "";
  let i = 0;
  while (i < message.length) {
    const open = message.indexOf("{", i);
    if (open < 0) return out + accent(message.slice(i));
    out += accent(message.slice(i, open));
    const close = closeOf(message, open);
    const inner = message.slice(open + 1, close);
    const m = /^(\s*\w+\s*,\s*plural\s*,)(.*)$/s.exec(inner);
    if (m) {
      // Keep the selector keywords; pseudo-localise each option's text.
      let opts = "";
      let j = 0;
      const body = m[2]!;
      while (j < body.length) {
        const o = body.indexOf("{", j);
        if (o < 0) {
          opts += body.slice(j);
          break;
        }
        const c = closeOf(body, o);
        opts += body.slice(j, o) + "{" + walk(body.slice(o + 1, c)) + "}";
        j = c + 1;
      }
      out += "{" + m[1] + opts + "}";
    } else {
      out += "{" + inner + "}";
    }
    i = close + 1;
  }
  return out;
}

export function pseudoLocalize(message: string): string {
  const letters = (message.replace(/\{[^{}]*\}|<[^>]*>/g, "").match(/[a-zA-Z]/g) ?? []).length;
  return `⟦${walk(message)}${"·".repeat(Math.ceil(letters * 0.35))}⟧`;
}

export function pseudoCatalogue<T>(messages: T): T {
  if (typeof messages === "string") return pseudoLocalize(messages) as T;
  return Object.fromEntries(
    Object.entries(messages as Record<string, unknown>).map(([k, v]) => [k, pseudoCatalogue(v)]),
  ) as T;
}
