import { percentDone } from "@/lib/growth";

/** Days done as text plus a bar; the text carries the information, the bar is decorative. */
export function Progress({ done, total, next }: { done: number; total: number; next: number | null }) {
  const pct = percentDone(done, total);
  return (
    <span className="mt-3 block">
      <span className="block text-sm">
        {done} of {total} days done{next ? ` · next: day ${next}` : " · finished"}
      </span>
      <span className="mt-1 block h-2 rounded-full bg-muted" aria-hidden>
        <span className="block h-2 rounded-full bg-primary" style={{ width: `${pct}%` }} />
      </span>
    </span>
  );
}
