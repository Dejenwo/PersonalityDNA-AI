/** A small ICU subset: {name}, {count, plural, one {...} other {...}} with # for the number. */
export type Vars = Record<string, string | number>;

function findClose(s: string, start: number): number {
  let depth = 0;
  for (let i = start; i < s.length; i++) {
    if (s[i] === "{") depth++;
    else if (s[i] === "}") {
      depth--;
      if (depth === 0) return i;
    }
  }
  return -1;
}

function plural(body: string, n: number, locale: string): string {
  const options: Record<string, string> = {};
  let i = 0;
  while (i < body.length) {
    const open = body.indexOf("{", i);
    if (open < 0) break;
    const key = body.slice(i, open).trim();
    const close = findClose(body, open);
    if (close < 0) break;
    options[key] = body.slice(open + 1, close);
    i = close + 1;
  }
  const rule = new Intl.PluralRules(locale).select(n);
  const chosen = options[`=${n}`] ?? options[rule] ?? options.other ?? "";
  return chosen.replace(/#/g, new Intl.NumberFormat(locale).format(n));
}

export function format(message: string, vars: Vars = {}, locale = "en"): string {
  let out = "";
  let i = 0;
  while (i < message.length) {
    const open = message.indexOf("{", i);
    if (open < 0) {
      out += message.slice(i);
      break;
    }
    out += message.slice(i, open);
    const close = findClose(message, open);
    if (close < 0) {
      out += message.slice(open);
      break;
    }
    const inner = message.slice(open + 1, close);
    const [name = "", kind, ...rest] = inner.split(",");
    const key = name.trim();
    if (kind?.trim() === "plural") {
      out += plural(rest.join(",").trim(), Number(vars[key] ?? 0), locale);
    } else {
      out += key in vars ? String(vars[key]) : `{${key}}`;
    }
    i = close + 1;
  }
  return out;
}

/** Placeholder and tag names in a message, for checking catalogues against the source. */
export function signature(message: string): string[] {
  const names = new Set<string>();
  for (const m of message.matchAll(/\{\s*([a-zA-Z_]\w*)\s*[,}]/g)) names.add(`{${m[1]}}`);
  for (const m of message.matchAll(/<([a-z]\w*)>/g)) names.add(`<${m[1]}>`);
  return [...names].sort();
}

export type RichPart = { text: string; tag?: string };

/** Splits "a <link>b</link> c" into parts so components can wrap tagged text. Tags don't nest. */
export function richParts(message: string): RichPart[] {
  const parts: RichPart[] = [];
  const re = /<([a-z]\w*)>(.*?)<\/\1>/g;
  let last = 0;
  for (const m of message.matchAll(re)) {
    if (m.index! > last) parts.push({ text: message.slice(last, m.index) });
    parts.push({ text: m[2]!, tag: m[1] });
    last = m.index! + m[0].length;
  }
  if (last < message.length) parts.push({ text: message.slice(last) });
  return parts;
}
