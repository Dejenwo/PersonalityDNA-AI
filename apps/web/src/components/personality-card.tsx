import type { PublicCard } from "@pdna/api-client";
import { BAND_LABEL } from "@/lib/reports";
import { BAND_POSITION } from "@/lib/share";

/** The public card. Bands are written out as text; the segments are decoration. */
export function PersonalityCard({ card }: { card: PublicCard }) {
  return (
    <div className="rounded-card border border-line bg-surface p-6 shadow-sm">
      <p className="text-sm text-ink-muted">PersonalityDNA</p>
      <p className="mt-1 text-2xl font-bold">{card.archetype ?? "Personality traits"}</p>
      {card.summary && <p className="mt-2">{card.summary}</p>}
      {card.traits.length > 0 && (
        <ul className="mt-4 space-y-2" aria-label="Big Five trait bands">
          {card.traits.map((t) => (
            <li key={t.name} className="grid grid-cols-[1fr_auto] items-center gap-3 sm:grid-cols-[12rem_1fr_auto]">
              <span className="font-medium">{t.name}</span>
              <span className="hidden gap-1 sm:flex" aria-hidden>
                {[0, 1, 2].map((i) => (
                  <span
                    key={i}
                    className={`h-3 flex-1 rounded-full ${i === BAND_POSITION[t.band] ? "bg-primary" : "bg-muted"}`}
                  />
                ))}
              </span>
              <span className="text-sm text-ink-muted">{BAND_LABEL[t.band]}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-4 text-sm text-ink-muted">
        {card.note} Created {card.created_on}.
      </p>
    </div>
  );
}
