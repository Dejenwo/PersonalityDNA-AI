import { Fragment, type ReactNode } from "react";

/** Known-safe links the coach may mention. Anything else is shown as plain text. */
const LINKS: Record<string, string> = { "findahelpline.com": "https://findahelpline.com" };

function inline(text: string, key: string): ReactNode[] {
  // **bold**, _italic_ and whitelisted links. No HTML is ever interpreted.
  const out: ReactNode[] = [];
  const pattern = /\*\*([^*]+)\*\*|(?<![\w])_([^_]+)_(?![\w])|(findahelpline\.com)/g;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = pattern.exec(text)) !== null) {
    if (m.index > last) out.push(text.slice(last, m.index));
    const k = `${key}-${i++}`;
    if (m[1] !== undefined) out.push(<strong key={k}>{m[1]}</strong>);
    else if (m[2] !== undefined) out.push(<em key={k}>{m[2]}</em>);
    else if (m[3] !== undefined)
      out.push(
        <a key={k} href={LINKS[m[3]]} className="underline" target="_blank" rel="noopener noreferrer">
          {m[3]}
        </a>,
      );
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/** Renders the coach's light Markdown (paragraphs, bullet lists, bold, italics) as React elements. */
export function CoachText({ text }: { text: string }) {
  const blocks = text.split(/\n{2,}/).filter((b) => b.trim());
  return (
    <div className="space-y-3">
      {blocks.map((block, b) => {
        const lines = block.split("\n");
        const bullets = lines.filter((l) => /^\s*[-*] /.test(l));
        const intro = lines.filter((l) => !/^\s*[-*] /.test(l));
        return (
          <Fragment key={b}>
            {intro.length > 0 && (
              <p>
                {intro.map((l, i) => (
                  <Fragment key={i}>
                    {i > 0 && <br />}
                    {inline(l, `${b}-${i}`)}
                  </Fragment>
                ))}
              </p>
            )}
            {bullets.length > 0 && (
              <ul className="list-disc space-y-1 pl-5">
                {bullets.map((l, i) => (
                  <li key={i}>{inline(l.replace(/^\s*[-*] /, ""), `${b}-li-${i}`)}</li>
                ))}
              </ul>
            )}
          </Fragment>
        );
      })}
    </div>
  );
}
