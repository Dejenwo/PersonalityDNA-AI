import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

const base =
  "inline-flex items-center justify-center gap-2 rounded-full px-5 py-3 text-base font-semibold transition-colors disabled:cursor-not-allowed disabled:opacity-50 min-h-12";
const variants = {
  primary: "bg-primary text-on-primary hover:opacity-90",
  secondary: "border border-line bg-surface text-ink hover:bg-muted",
  ghost: "text-primary hover:bg-muted",
} as const;

type Variant = keyof typeof variants;

export function Button({ variant = "primary", className = "", ...props }: ComponentProps<"button"> & { variant?: Variant }) {
  return <button className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function ButtonLink({
  variant = "primary",
  className = "",
  ...props
}: ComponentProps<typeof Link> & { variant?: Variant }) {
  return <Link className={`${base} ${variants[variant]} ${className}`} {...props} />;
}

export function Card({ children, className = "", as: Tag = "section", ...rest }: {
  children: ReactNode;
  className?: string;
  as?: "section" | "article" | "div";
} & Record<string, unknown>) {
  return (
    <Tag className={`rounded-card border border-line bg-surface p-5 sm:p-6 ${className}`} {...rest}>
      {children}
    </Tag>
  );
}

export function ProgressBar({ value, label }: { value: number; label: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-valuenow={Math.round(pct)}
      className="h-2 w-full overflow-hidden rounded-full bg-muted"
    >
      <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${pct}%` }} />
    </div>
  );
}

export function LoadingState({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center gap-3 py-16 text-ink-muted">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-line border-t-primary" aria-hidden />
      <span>{label}…</span>
    </div>
  );
}

export function ErrorState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <Card className="my-8" role="alert">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-ink-muted">{message}</p>
      {action ? <div className="mt-4 flex flex-wrap gap-3">{action}</div> : null}
    </Card>
  );
}

export function EmptyState({ title, message, action }: { title: string; message: string; action?: ReactNode }) {
  return (
    <Card className="my-8 text-center">
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-ink-muted">{message}</p>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </Card>
  );
}
