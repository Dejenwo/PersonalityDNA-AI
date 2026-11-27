# App store launch

**Status: the mobile app is not built, so nothing can be submitted yet.** It needs the Expo app, Apple and Google
developer accounts and the owner's approval. This page collects what can be prepared now.

## Before submission

- Bundle id `com.personalitydna.ai` (from MASTER_PROMPT.md; confirm it is available in both stores).
- Account deletion inside the app (Apple requires it) and a web link for Google: `/account` already offers it.
- In-app purchases through Apple and Google for digital content, with RevenueCat (docs/MONETIZATION.md).
- Sign in with Apple only becomes required if other social sign-in options are added.
- Age rating: the app is for adults (18+); answer the questionnaires accordingly.
- A demo account for reviewers, plus review notes saying results are non-clinical and that the coach is an AI.
- Accessibility: VoiceOver and TalkBack pass before submission.

## Store listing draft

To be checked by the scientific and legal reviewers (docs/review/) before use. No claims of accuracy,
validation, health benefits or outcomes.

- **Name:** PersonalityDNA (subtitle: Big Five personality and growth)
- **Short description:** Understand your personality with a free Big Five assessment, then reflect and grow.
- **Description:**
  Take a free Big Five personality assessment built on public-domain questionnaires from the International
  Personality Item Pool. See clear, balanced results: where you sit on each trait, your strengths and areas you
  might want to develop, with plain explanations of how scores are worked out.

  Then keep going: explore career interests and leadership preferences, follow growth programmes, write a
  private journal, set goals and habits, compare with someone you trust (with both your consent), and talk
  through your results with an AI coach.

  Private by default: your journal, goals and coaching are encrypted, and our team can't read them. No ads, no
  trackers, and your data is never sold. Download or delete everything at any time.

  PersonalityDNA is for self-reflection and personal development. It isn't a clinical or diagnostic tool and must
  not be used for hiring decisions.
- **Keywords (to research):** personality test, Big Five, OCEAN, self-reflection, personal growth, journal.
  No competitor or trademarked test names.
- **Screenshots:** home, a question, the result summary, a trait explanation, growth programme, journal. Phone
  and tablet sizes; light and dark.

## Privacy labels (Apple) and data safety (Google)

From the data inventory in docs/PRIVACY_REQUIREMENTS.md. Counsel to confirm.

| Data | Collected | Linked to the person | Used for tracking | Purpose |
| --- | --- | --- | --- | --- |
| Email address | Yes, with an account | Yes | No | Account, security notices, optional reminders |
| Assessment answers and results | Yes | Yes with an account; device-only without | No | App functionality |
| Journal, goals and other content the person writes | Yes | Yes | No | App functionality (encrypted) |
| Coaching messages | Yes, if the coach is used | Yes | No | App functionality; sent to the AI provider only with consent |
| Purchases | Yes, with a subscription | Yes | No | App functionality |
| Feedback messages | Yes, if sent | Only if signed in | No | Product improvement and support |
| Product interaction | Daily counts only, with no identifier | No | No | Analytics |
| Location, contacts, device id, advertising id | No | | | |

Data is encrypted in transit. People can ask for deletion in the app. No data is shared with third parties for
their own purposes; processors (hosting, email, payments, the AI provider when the coach is used) act for us.
