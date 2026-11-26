"use client";

import type { AssessmentDetail } from "@pdna/api-client";

interface Props {
  itemId: string;
  number: number;
  text: string;
  options: AssessmentDetail["response_options"];
  value: number | undefined;
  onChange: (value: number) => void;
}

/** One statement with its response options, as a native radio group (keyboard and screen-reader friendly). */
export function LikertQuestion({ itemId, number, text, options, value, onChange }: Props) {
  return (
    <fieldset>
      <legend className="text-2xl font-semibold leading-snug sm:text-3xl">
        <span className="sr-only">Statement {number}: </span>
        {text}
      </legend>
      <p className="mt-2 text-ink-muted">How accurately does this describe you?</p>
      <div className="mt-6 grid gap-3">
        {options.map((o) => {
          const id = `${itemId}-${o.value}`;
          const checked = value === o.value;
          return (
            <label
              key={o.value}
              htmlFor={id}
              className={`flex min-h-14 cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-base transition-colors ${
                checked ? "border-primary bg-muted font-semibold" : "border-line bg-surface hover:bg-muted"
              }`}
            >
              <input
                id={id}
                type="radio"
                name={itemId}
                value={o.value}
                checked={checked}
                onChange={() => onChange(o.value)}
                className="h-5 w-5 accent-[var(--pdna-primary)]"
              />
              {o.label}
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
