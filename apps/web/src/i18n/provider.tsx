"use client";

import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { en, type Messages } from "./messages/en";
import { format, richParts, type Vars } from "./format";
import { LOCALES, PREVIEW, resolveLocale, selectableLocales, type LocaleInfo } from "./locales";
import { pseudoCatalogue } from "./pseudo";
import { CATALOGUES } from "./catalogues";

const STORAGE_KEY = "pdna.locale.v1";

type Path<T, P extends string = ""> = {
  [K in keyof T & string]: T[K] extends string ? `${P}${K}` : Path<T[K], `${P}${K}.`>;
}[keyof T & string];
export type MessageKey = Path<Messages>;

const pseudo: Record<string, Messages> = {};

export function catalogueFor(code: string): Messages {
  const info = LOCALES.find((l) => l.code === code);
  if (info?.pseudo) return (pseudo[code] ??= pseudoCatalogue(en));
  return CATALOGUES[code] ?? en;
}

export function lookup(messages: Messages, key: string): string {
  let node: unknown = messages;
  for (const part of key.split(".")) node = (node as Record<string, unknown> | undefined)?.[part];
  if (typeof node === "string") return node;
  // Fall back to English for a missing key rather than showing the key.
  let fallback: unknown = en;
  for (const part of key.split(".")) fallback = (fallback as Record<string, unknown> | undefined)?.[part];
  return typeof fallback === "string" ? fallback : key;
}

interface I18n {
  locale: string;
  info: LocaleInfo;
  locales: LocaleInfo[];
  setLocale: (code: string) => void;
  t: (key: MessageKey, vars?: Vars) => string;
  rich: (key: MessageKey, tags: Record<string, (text: string) => ReactNode>, vars?: Vars) => ReactNode[];
  formatDate: (value: string | Date, style?: Intl.DateTimeFormatOptions["dateStyle"]) => string;
  formatNumber: (value: number) => string;
  formatMoney: (cents: number, currency: string) => string;
}

const Ctx = createContext<I18n | null>(null);

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

export function I18nProvider({ children, onChange }: { children: ReactNode; onChange?: (code: string) => void }) {
  // The server renders English; the stored or browser choice applies after hydration.
  const [locale, setState] = useState("en");
  useEffect(() => {
    const chosen = resolveLocale(readStored(), typeof navigator === "undefined" ? [] : navigator.languages);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reading browser-only state after hydration
    if (chosen !== "en") setState(chosen);
  }, []);
  const info = LOCALES.find((l) => l.code === locale) ?? LOCALES[0]!;
  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = info.direction;
  }, [locale, info.direction]);

  const setLocale = useCallback(
    (code: string) => {
      const target = selectableLocales(PREVIEW).find((l) => l.code === code);
      if (!target) return;
      try {
        window.localStorage.setItem(STORAGE_KEY, code);
      } catch {
        /* storage blocked: the choice lasts for this page view */
      }
      setState(code);
      onChange?.(code);
    },
    [onChange],
  );

  const value = useMemo<I18n>(() => {
    const messages = catalogueFor(locale);
    const t = (key: MessageKey, vars?: Vars) => format(lookup(messages, key), vars, locale);
    return {
      locale,
      info,
      locales: selectableLocales(PREVIEW),
      setLocale,
      t,
      rich: (key, tags, vars) =>
        richParts(t(key, vars)).map((p, i) => {
          const wrap = p.tag ? tags[p.tag] : undefined;
          return wrap ? <span key={i}>{wrap(p.text)}</span> : p.text;
        }),
      formatDate: (v, style = "medium") => new Date(v).toLocaleDateString(locale, { dateStyle: style }),
      formatNumber: (n) => new Intl.NumberFormat(locale).format(n),
      formatMoney: (cents, currency) => new Intl.NumberFormat(locale, { style: "currency", currency }).format(cents / 100),
    };
  }, [locale, info, setLocale]);

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useI18n must be used inside I18nProvider");
  return ctx;
}
