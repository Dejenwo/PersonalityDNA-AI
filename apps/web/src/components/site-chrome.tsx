import Link from "next/link";
import { AuthNav } from "./auth-nav";

export function SiteHeader() {
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-bold text-ink" aria-label="PersonalityDNA AI home">
          <span aria-hidden className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-on-primary">
            ◆
          </span>
          PersonalityDNA
        </Link>
        <nav aria-label="Main">
          <ul className="flex flex-wrap items-center gap-1 text-sm font-medium">
            <li>
              <Link href="/discover" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                Discover
              </Link>
            </li>
            <li>
              <Link href="/careers" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                Careers
              </Link>
            </li>
            <li>
              <Link href="/learn" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                Learn
              </Link>
            </li>
            <li>
              <Link href="/history" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                My results
              </Link>
            </li>
            <AuthNav />
          </ul>
        </nav>
      </div>
    </header>
  );
}

export function SiteFooter() {
  return (
    <footer className="mt-16 border-t border-line">
      <div className="mx-auto max-w-5xl px-4 py-8 text-sm text-ink-muted">
        <p>
          PersonalityDNA is for self-reflection and personal development. It is not a clinical or diagnostic tool and
          must not be used for hiring decisions.
        </p>
        <p className="mt-2">
          Big Five items from the{" "}
          <a className="underline" href="https://ipip.ori.org/" rel="noopener noreferrer" target="_blank">
            International Personality Item Pool
          </a>{" "}
          (public domain). <Link className="underline" href="/privacy">Privacy notice</Link>
        </p>
      </div>
    </footer>
  );
}
