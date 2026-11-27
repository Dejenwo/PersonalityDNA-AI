"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/provider";
import { AuthNav } from "./auth-nav";
import { LanguageSelect } from "./language-select";

export function SiteHeader() {
  const { t } = useI18n();
  return (
    <header className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-x-4 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-bold text-ink" aria-label={t("nav.home", { brand: "PersonalityDNA" })}>
          <span aria-hidden className="grid h-8 w-8 place-items-center rounded-lg bg-primary text-on-primary">
            ◆
          </span>
          PersonalityDNA
        </Link>
        <nav aria-label={t("nav.main")}>
          <ul className="flex flex-wrap items-center gap-1 text-sm font-medium">
            <li>
              <Link href="/discover" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                {t("nav.discover")}
              </Link>
            </li>
            <li>
              <Link href="/careers" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                {t("nav.careers")}
              </Link>
            </li>
            <li>
              <Link href="/learn" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                {t("nav.learn")}
              </Link>
            </li>
            <li>
              <Link href="/history" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
                {t("nav.results")}
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
  const { t, rich } = useI18n();
  return (
    <footer className="mt-16 border-t border-line">
      <div className="mx-auto max-w-5xl px-4 py-8 text-sm text-ink-muted">
        <p>{t("footer.disclaimer")}</p>
        <p className="mt-2">
          {rich("footer.items", {
            ipip: (text) => (
              <a className="underline" href="https://ipip.ori.org/" rel="noopener noreferrer" target="_blank">
                {text}
              </a>
            ),
          })}{" "}
          <Link className="underline" href="/privacy">
            {t("footer.privacy")}
          </Link>{" "}
          ·{" "}
          <Link className="underline" href="/pricing">
            {t("footer.pricing")}
          </Link>{" "}
          ·{" "}
          <Link className="underline" href="/orgs">
            {t("footer.organisations")}
          </Link>
        </p>
        <div className="mt-4">
          <LanguageSelect id="footer-language" label={t("footer.language")} />
        </div>
      </div>
    </footer>
  );
}
