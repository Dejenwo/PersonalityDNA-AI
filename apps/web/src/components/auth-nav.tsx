"use client";

import Link from "next/link";
import { useI18n } from "@/i18n/provider";
import { useAuth } from "@/lib/auth";

export function AuthNav() {
  const { state } = useAuth();
  const { t } = useI18n();
  if (state.status === "loading") return <li aria-hidden className="w-16" />;
  if (state.status === "signed-in") {
    return (
      <>
        <li>
          <Link href="/coach" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            {t("nav.coach")}
          </Link>
        </li>
        <li>
          <Link href="/journal" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            {t("nav.journal")}
          </Link>
        </li>
        <li>
          <Link href="/goals" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            {t("nav.goals")}
          </Link>
        </li>
        <li>
          <Link href="/relationships" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            {t("nav.relationships")}
          </Link>
        </li>
        <li>
          <Link href="/account" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
            {t("nav.account")}
          </Link>
        </li>
      </>
    );
  }
  return (
    <li>
      <Link href="/login" className="rounded-full px-2 py-2 hover:bg-muted sm:px-3">
        {t("nav.signIn")}
      </Link>
    </li>
  );
}
