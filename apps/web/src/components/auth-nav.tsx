"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useI18n } from "@/i18n/provider";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Unread count, refreshed on each navigation. A failed check just hides the badge. */
function NotificationsLink({ userId }: { userId: string }) {
  const { t, formatNumber } = useI18n();
  const pathname = usePathname();
  const [unread, setUnread] = useState(0);
  useEffect(() => {
    let alive = true;
    api.notifications().then(
      (page) => alive && setUnread(page.unread),
      () => alive && setUnread(0),
    );
    return () => {
      alive = false;
    };
  }, [userId, pathname]);
  const label = unread > 0 ? t("nav.notificationsUnread", { count: formatNumber(unread) }) : t("nav.notifications");
  return (
    <Link
      href="/notifications"
      aria-label={label}
      className="relative inline-flex items-center rounded-full px-2 py-2 hover:bg-muted sm:px-3"
    >
      <svg aria-hidden viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M6 8a6 6 0 1 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
        <path d="M10.3 21a1.94 1.94 0 0 0 3.4 0" />
      </svg>
      {unread > 0 && (
        <span
          aria-hidden
          className="absolute -top-0.5 end-0 min-w-5 rounded-full bg-primary px-1 text-center text-xs font-semibold text-on-primary"
        >
          {unread > 9 ? "9+" : unread}
        </span>
      )}
    </Link>
  );
}

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
        <li>
          <NotificationsLink userId={state.user.id} />
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
