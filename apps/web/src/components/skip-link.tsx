"use client";

import { useI18n } from "@/i18n/provider";

export function SkipLink() {
  const { t } = useI18n();
  return (
    <a
      href="#main"
      className="sr-only focus:not-sr-only focus:absolute focus:start-4 focus:top-4 focus:z-50 focus:rounded focus:bg-surface focus:p-3"
    >
      {t("common.skipToContent")}
    </a>
  );
}
