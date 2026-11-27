# Scientific review packet

For a qualified psychometrician or personality psychologist. Please check that everything the app shows is
accurate, balanced and no stronger than the evidence allows. Nothing here has been reviewed yet.

## What the app is

A self-reflection and personal development app. It is not clinical, not diagnostic and not for hiring. It
shows no percentiles (there are no norms), makes no predictions about people, and labels original,
unvalidated content as such.

## Please review

| # | Item | Where | Questions for the reviewer |
| --- | --- | --- | --- |
| 1 | Mini-IPIP (20 items) and IPIP Big-Five Factor Markers (50 items): wording, keying and scale membership | `assessment-content/instruments/mini-ipip-20.v1.0.0.json`, `ipip-bfm-50.v1.0.0.json`; licence `assessment-content/licenses/IPIP.md` | Do items, keys and scale assignments match the published IPIP versions? |
| 2 | Scoring: reversed items, minimum answered items per trait (8 of 10, or 4 of 4), mean of answered items, rescaled to 0 to 100 | `assessment-content/scoring-rules/big-five-likert.v1.json`, `docs/ASSESSMENT_METHODOLOGY.md`, `services/backend/app/scoring/engine.py` | Is the method correct and clearly explained? Is a 0 to 100 display misleading without norms? |
| 3 | Bands: lower (under 40), middle (40 to 60), higher (over 60) on the 0 to 100 display scale, describing position on the response scale rather than relative to other people | same files | Are these fixed cut points defensible, and is the band wording appropriate? |
| 4 | Response quality flags: 10 or more identical answers, and under 1.5 seconds per item. Flags are shown but never change scores | `docs/ASSESSMENT_METHODOLOGY.md` | Are these heuristics sensible, and are the messages to users fair? |
| 5 | Trait interpretations: descriptions, strengths, growth areas, communication tips | `assessment-content/scoring-rules/trait-interpretations.v1.json` | Is each statement supported? Are both ends of every trait described without value judgement? |
| 6 | Personality archetypes (profile names built from band patterns) | `assessment-content/scoring-rules/archetypes.v1.json`, `docs/PERSONALITY_ARCHETYPES.md` | Are they presented as descriptive summaries rather than types? Any stereotyping? |
| 7 | Relationship comparison text (similarities, differences, likely misunderstandings, prompts) | `assessment-content/scoring-rules/relationship-insights.v1.json` | No compatibility scores or predictions are shown. Is the language suitably tentative? |
| 8 | Career interests (O*NET Interest Profiler Short Form, draft) and how they are combined with Big Five working style | `onet-ipsf-60.v1.0.0.json`, `interest-interpretations.v1.json`, `assessment-content/licenses/ONET.md`, K-16 | Do items and area keys match the official form? Is the career exploration framed as exploration, not advice? |
| 9 | Leadership preferences questionnaire (original, 27 statements, unvalidated) | `leadership-preferences-27.v1.0.0.json`, `leadership-program.v1.json`, `assessment-content/licenses/ORIGINAL_CONTENT.md` | Is it clearly labelled as reflection, not a measure of ability? Should it be released at all before a validation study? |
| 10 | Emotional awareness track and growth programmes (original content, no scores) | `emotional-awareness.v1.json`, `growth-academy.v1.json` | Any claims about effectiveness? Anything that needs a clinician (see the legal and clinical packet)? |
| 11 | Personality reports (methodology, references, limitations sections) | `report-content.v1.json` | Are the references accurate and the limitations complete? |
| 12 | AI coach instructions: what it may say about results | `ai/prompts/coach.v1.md`, `docs/AI_SAFETY.md` | Does it keep to the results, avoid diagnosis and avoid overclaiming? |
| 13 | Public article on the Big Five | `apps/web/src/app/big-five/page.tsx` | Is it accurate, and are the citations right? |
| 14 | Validation study plan | `docs/SCIENTIFIC_VALIDATION_PLAN.md` | Is the plan sound, and what must happen before any accuracy claim? |

## How to give feedback

Please mark each row as approved, approved with changes or not approved, with comments. Released content is
never edited in place: changes become a new content version, and scoring changes increase the engine
version, so earlier results stay reproducible.

## Sign-off

| Reviewer | Qualification | Date | Decision |
| --- | --- | --- | --- |
| | | | |
