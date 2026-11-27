import registry from "./locales.json";

export interface LocaleInfo {
  code: string;
  name: string;
  native_name: string;
  direction: "ltr" | "rtl";
  status: "planned" | "in_review" | "released";
  /** Generated test locales, only offered in preview builds. */
  pseudo?: boolean;
}

/** Same registry as the API (services/backend/app/i18n/locales.v1.json; a test keeps them equal). */
export const REGISTRY = registry as { version: string; default: string; note: string; locales: LocaleInfo[] };

const PSEUDO: LocaleInfo[] = [
  { code: "en-XA", name: "Pseudo (accented)", native_name: "Ƥšéúðó", direction: "ltr", status: "in_review", pseudo: true },
  { code: "ar-XB", name: "Pseudo (right to left)", native_name: "Ƥšéúðó ŔŢĽ", direction: "rtl", status: "in_review", pseudo: true },
];

export const LOCALES: LocaleInfo[] = [...REGISTRY.locales, ...PSEUDO];

/** Preview builds (NEXT_PUBLIC_I18N_PREVIEW=true) also offer the pseudo-locales for testing. */
export const PREVIEW = process.env.NEXT_PUBLIC_I18N_PREVIEW === "true";

export function selectableLocales(preview: boolean): LocaleInfo[] {
  return LOCALES.filter((l) => l.status === "released" || (preview && l.pseudo));
}

/** A stored choice if it is still selectable, else the best released match for the browser's languages. */
export function resolveLocale(stored: string | null, browser: readonly string[], preview: boolean = PREVIEW): string {
  const options = selectableLocales(preview);
  if (stored && options.some((l) => l.code === stored)) return stored;
  const released = options.filter((l) => !l.pseudo);
  for (const tag of browser) {
    const hit = released.find((l) => l.code === tag) ?? released.find((l) => l.code === tag.split("-")[0]);
    if (hit) return hit.code;
  }
  return REGISTRY.default;
}
