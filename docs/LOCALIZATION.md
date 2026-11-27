# Localisation

How PersonalityDNA adds languages. English is the only released language. The governing rule (MASTER_PROMPT §18): translating personality questions does not by itself preserve their meaning or measurement properties, so assessment content in a new language needs a cultural adaptation review before release.

## What is built (Phase 19)

| Part | Where | Notes |
| --- | --- | --- |
| Language registry | `services/backend/app/i18n/locales.v1.json`, copied to `apps/web/src/i18n/locales.json` | The ten languages from the spec, each `planned`, `in_review` or `released`, with text direction. A web test fails if the two copies differ. `GET /api/v1/locales` serves it. |
| Interface messages | `apps/web/src/i18n/messages/en.ts` | English source catalogue. A small ICU subset: `{name}`, `{count, plural, one {…} other {…}}`, and `<tag>text</tag>` for links. Tests check that every catalogue keeps the source keys, placeholders and tags. |
| Reviewed catalogues | `apps/web/src/i18n/catalogues.ts` | Only reviewed catalogues go here. A missing message falls back to English key by key, never to a raw key. |
| Choosing a language | Footer and account page | Only released languages can be chosen. The choice is kept on the device, and for signed-in people a released language is saved to the profile (`PATCH /api/v1/me`; anything else returns 422 `locale_unavailable`). Without a choice, the browser's languages are matched against released languages. |
| Formatting | `useI18n()` | Dates, numbers and money through `Intl` with the active locale. |
| Right-to-left | `<html dir>` and logical CSS | The provider sets `lang` and `dir`. Components use logical utilities (`ps-`, `ms-`, `start-`, `text-start`), so layouts mirror. |
| Pseudo-locales | `en-XA` (accented, longer) and `ar-XB` (right to left) | Generated from English. They're offered only in preview builds (`NEXT_PUBLIC_I18N_PREVIEW=true`, used by CI's end-to-end run) to find hard-coded text, truncation and mirroring problems. They are never saved to a profile. |
| Translated instruments | `Instrument.adaptation` in `app/assessments/content.py` | Any instrument whose `locale` isn't English must carry an adaptation record (source instrument, method, status, reviewers, evidence). It can't be `released` until the status is `approved` with named reviewers. Until then it can only exist as a draft, and drafts are hidden in production. |
| Admin view | Admin portal, Content tab, "Languages" | Release status, direction and how much interface text each language has. Instruments and content files show their language and adaptation status. |

Screens migrated to messages so far: the site header and navigation, the footer, the skip link, and the language settings. The other screens are still English-only text in components and move to messages screen by screen (I-003). Until then a non-English interface would be mixed. That is acceptable only because no other language is released.

## Releasing a new interface language

1. Set the language to `in_review` in both registry files.
2. Have a professional translator produce `messages/<code>.ts`, starting from the English source with each message's context. The type `Messages` makes the compiler insist on every key.
3. Get a review by a second native speaker for meaning, tone (warm, non-clinical, non-judgemental) and safety wording (crisis and "not clinical, not for hiring" texts).
4. Check it in the preview build: no clipped text, and for right-to-left languages correct mirroring and number direction.
5. Add the catalogue to `catalogues.ts`. Set the status to `released` in both registry files in the same pull request, and record the reviewers in the pull request.

Educational content (learning tracks, growth programmes, interpretations, report text, emails) follows the same review. Each content file carries a `locale`, and a translated file is a new file, not an edit of the English one.

## Adapting an assessment to another language

Following the ITC Guidelines for Translating and Adapting Tests (2nd ed., 2017) as the reference process. No step can be skipped by an agent.

1. **Licence check.** Confirm the licence allows translations and adaptations. IPIP items are public domain. The O*NET Interest Profiler is CC BY-ND, so translations need permission.
2. **Forward translation.** Two independent translators, then a reconciled version (`team_translation`), or forward and back translation (`translation_back_translation`).
3. **Expert review.** Bilingual subject-matter and psychometric reviewers check each item's meaning, cultural fit and reading level, and record their decisions.
4. **Cognitive interviews.** A small sample of target-language speakers explains how they read each item. Items are revised where readings diverge.
5. **Pilot and analysis.** Collect responses with consent. Check reliability, factor structure, and measurement invariance against the source language before comparing scores across languages.
6. **Release.** Add a new instrument file with the target `locale`, `status: "draft"` and an `adaptation` record with `status: "in_review"`. When reviewers approve it, publish a new version with `status: "released"` and `adaptation.status: "approved"`, the reviewers, and references to the evidence. Never present it as validated beyond what the evidence shows, and never show norms or percentiles without norm data from that population.

## Not built yet

- Server-rendered language (pages render English first and switch after loading). This is fine while English is the only released language. A locale route segment or cookie-based rendering comes with the first released translation.
- Localised emails and notifications. The profile language is stored for this.
- Localised PDF fonts for non-Latin scripts.
- A translation management service. Catalogues live in the repository and are reviewed in pull requests.
