/**
 * English source messages. Every other catalogue has exactly these keys and placeholders (checked by tests).
 * Placeholders: {name}; plurals: {count, plural, one {# item} other {# items}}; links: <tag>text</tag>.
 */
export const en = {
  common: {
    skipToContent: "Skip to content",
    loading: "Loading",
  },
  nav: {
    main: "Main",
    home: "{brand} AI home",
    discover: "Discover",
    careers: "Careers",
    learn: "Learn",
    results: "My results",
    coach: "Coach",
    journal: "Journal",
    goals: "Goals",
    relationships: "Relationships",
    account: "Account",
    notifications: "Notifications",
    notificationsUnread: "Notifications, {count} unread",
    signIn: "Sign in",
  },
  footer: {
    disclaimer:
      "PersonalityDNA is for self-reflection and personal development. It is not a clinical or diagnostic tool and must not be used for hiring decisions.",
    items: "Big Five items from the <ipip>International Personality Item Pool</ipip> (public domain).",
    privacy: "Privacy notice",
    pricing: "Plans and pricing",
    organisations: "For organisations",
    language: "Language",
  },
  language: {
    title: "Language",
    body: "English is available now. More languages are coming after review by native speakers; assessment questions are only offered in a language once they have been carefully adapted and checked.",
    label: "Display language",
    saved: "Language saved.",
    preview: "{name} (preview)",
    untranslated: "{count, plural, one {# text is} other {# texts are}} not translated yet and show in English.",
  },
} as const;

type Widen<T> = { [K in keyof T]: T[K] extends string ? string : Widen<T[K]> };
export type Messages = Widen<typeof en>;
