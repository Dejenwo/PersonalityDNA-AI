import type { TraitResult } from "@pdna/api-client";

const bandLabel = { lower: "Lower", middle: "Middle", higher: "Higher" } as const;

/** Horizontal 0-100 bar. The number and band are shown as text so the chart is never the only carrier. */
export function TraitBar({ trait }: { trait: TraitResult }) {
  const score = trait.score ?? 0;
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-lg font-semibold">{trait.name}</h3>
        <p className="text-sm text-ink-muted">
          {trait.status === "scored" ? (
            <>
              <span className="text-base font-semibold text-ink">{score.toFixed(0)}</span> / 100
              {trait.band ? ` · ${bandLabel[trait.band]}` : ""}
            </>
          ) : (
            "Not enough answers"
          )}
        </p>
      </div>
      <div className="relative mt-2 h-3 rounded-full bg-muted" aria-hidden>
        <div className="absolute inset-y-0 start-[40%] w-[20%] bg-line/60" />
        <div className="absolute inset-y-0 start-0 rounded-full bg-primary" style={{ width: `${score}%` }} />
      </div>
      <p className="mt-1 text-sm text-ink-muted">{trait.description}</p>
    </div>
  );
}
