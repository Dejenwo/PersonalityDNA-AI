"use client";

import { useState } from "react";
import { useI18n } from "@/i18n/provider";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

/** Changes the display language; for signed-in people a released language is also saved to their profile. */
export function LanguageSelect({ id, label, onSaved }: { id: string; label: string; onSaved?: () => void }) {
  const { locale, locales, setLocale, t } = useI18n();
  const { state, setUser } = useAuth();
  const [busy, setBusy] = useState(false);

  async function change(code: string) {
    setLocale(code);
    const target = locales.find((l) => l.code === code);
    if (state.status !== "signed-in" || !target || target.pseudo || state.user.locale === code) return;
    setBusy(true);
    try {
      setUser(await api.updateMe({ locale: code }));
      onSaved?.();
    } catch {
      /* the display language still changed on this device */
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={locale}
        disabled={busy}
        onChange={(e) => change(e.target.value)}
        className="rounded-card border border-line bg-surface px-2 py-1 text-ink"
      >
        {locales.map((l) => (
          <option key={l.code} value={l.code} lang={l.pseudo ? undefined : l.code}>
            {l.pseudo ? t("language.preview", { name: l.name }) : l.native_name}
          </option>
        ))}
      </select>
    </div>
  );
}
