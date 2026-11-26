# Design system

Source: `packages/design-tokens/src/index.ts` (TypeScript, for mobile and tests) mirrored in `tokens.css` (web). Tests fail if they drift or if any text pairing falls below WCAG AA 4.5:1.

## Colour

| Role | Light | Dark |
| --- | --- | --- |
| Background | warm off-white `#fbfaf7` | charcoal `#0e1117` |
| Surface | white | `#151924` |
| Text | deep navy `#0f1b3d` | `#eef0f7` |
| Muted text | `#4a5168` | `#9aa1b9` |
| Primary (indigo) | `#4338ca` | `#a5a0f5` |
| Accent (teal) | `#0d7a72` | `#2bbfb1` |
| Muted surface (lavender) | `#efedfb` | `#1e2433` |

Dark mode follows the system setting. A manual toggle comes with user preferences (Phase 5).

## Type, spacing, shape

Inter/system UI stack; body 16px minimum; 1.5 line height. 4px spacing scale. Radius 10px controls, 16px cards, pill buttons. Touch targets at least 48px tall.

## Components (web, `apps/web/src/components`)

`Button`, `ButtonLink`, `Card`, `ProgressBar` (ARIA progressbar), `LoadingState` (role=status), `ErrorState` (role=alert), `EmptyState`, `LikertQuestion` (native radio group in a fieldset), `TraitBar` (bar plus text value, never colour-only). A shared `packages/ui` for web and mobile is planned once the Expo app exists.

## Accessibility rules

Skip link, visible focus ring, focus moved to each new statement, reduced-motion respected, charts always paired with text values, form errors announced. axe scans run in end-to-end tests.

## Voice

Supportive, plain and specific. "You describe yourself as…" rather than "You are…". No trait is framed as good or bad. No urgency or guilt in prompts.

## Still to do

App icon and brand mark (owner input), mobile navigation (Home, Discover, AI Coach, Growth, Profile), chart components for history comparison, illustrations.
