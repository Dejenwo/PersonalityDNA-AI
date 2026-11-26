import type { ComponentProps } from "react";

export function TextField({
  label,
  hint,
  error,
  id,
  ...props
}: ComponentProps<"input"> & { label: string; hint?: string; error?: string | null; id: string }) {
  const describedBy = [hint ? `${id}-hint` : null, error ? `${id}-error` : null].filter(Boolean).join(" ") || undefined;
  return (
    <div>
      <label htmlFor={id} className="block font-medium">
        {label}
      </label>
      {hint && (
        <p id={`${id}-hint`} className="text-sm text-ink-muted">
          {hint}
        </p>
      )}
      <input
        id={id}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className="mt-1 block min-h-12 w-full rounded-xl border border-line bg-surface px-4 py-2 text-base text-ink"
        {...props}
      />
      {error && (
        <p id={`${id}-error`} className="mt-1 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}

export function FormMessage({ kind, children }: { kind: "error" | "success"; children: React.ReactNode }) {
  return (
    <p role={kind === "error" ? "alert" : "status"} className={kind === "error" ? "text-danger" : "text-accent"}>
      {children}
    </p>
  );
}
