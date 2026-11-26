/**
 * PersonalityDNA design tokens. Single source for colour, type, spacing and radius.
 * tokens.css mirrors these values as CSS variables for web; mobile imports this module.
 * contrast.test.ts checks every text/background pairing meets WCAG 2.2 AA (4.5:1).
 */

export const palette = {
  navy900: "#0f1b3d",
  navy800: "#16244f",
  navy700: "#1f3268",
  indigo600: "#4338ca",
  indigo500: "#5b50e0",
  indigo300: "#a5a0f5",
  teal600: "#0d7a72",
  teal400: "#2bbfb1",
  lavender100: "#efedfb",
  lavender200: "#dedaf7",
  offWhite: "#fbfaf7",
  white: "#ffffff",
  charcoal950: "#0e1117",
  charcoal900: "#151924",
  charcoal800: "#1e2433",
  slate600: "#4a5168",
  slate400: "#9aa1b9",
  slate200: "#e3e5ee",
  danger600: "#b42318",
  danger300: "#fda29b",
} as const;

export interface ThemeColors {
  background: string;
  surface: string;
  surfaceMuted: string;
  text: string;
  textMuted: string;
  border: string;
  primary: string;
  primaryText: string;
  accent: string;
  accentText: string;
  focus: string;
  danger: string;
}

export const light: ThemeColors = {
  background: palette.offWhite,
  surface: palette.white,
  surfaceMuted: palette.lavender100,
  text: palette.navy900,
  textMuted: palette.slate600,
  border: palette.slate200,
  primary: palette.indigo600,
  primaryText: palette.white,
  accent: palette.teal600,
  accentText: palette.white,
  focus: palette.indigo500,
  danger: palette.danger600,
};

export const dark: ThemeColors = {
  background: palette.charcoal950,
  surface: palette.charcoal900,
  surfaceMuted: palette.charcoal800,
  text: "#eef0f7",
  textMuted: palette.slate400,
  border: "#2b3347",
  primary: palette.indigo300,
  primaryText: palette.navy900,
  accent: palette.teal400,
  accentText: palette.navy900,
  focus: palette.indigo300,
  danger: palette.danger300,
};

export const typography = {
  fontFamily: "'Inter', system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif",
  // rem sizes; base 16px. Body never below 1rem for readability.
  size: { xs: 0.8125, sm: 0.875, base: 1, lg: 1.125, xl: 1.375, "2xl": 1.75, "3xl": 2.25 },
  lineHeight: { tight: 1.2, normal: 1.5 },
} as const;

export const space = { 1: 4, 2: 8, 3: 12, 4: 16, 5: 24, 6: 32, 7: 48, 8: 64 } as const;
export const radius = { sm: 6, md: 10, lg: 16, pill: 999 } as const;

/** Text/background pairs that must meet WCAG AA. */
export const contrastPairs = (t: ThemeColors): Array<[string, string, string]> => [
  ["text on background", t.text, t.background],
  ["text on surface", t.text, t.surface],
  ["text on surfaceMuted", t.text, t.surfaceMuted],
  ["textMuted on background", t.textMuted, t.background],
  ["textMuted on surface", t.textMuted, t.surface],
  ["primaryText on primary", t.primaryText, t.primary],
  ["accentText on accent", t.accentText, t.accent],
  ["danger on surface", t.danger, t.surface],
  ["primary on surface", t.primary, t.surface],
];
