# Assessment methodology

Applies to engine version 1.0.0, instruments `ipip-bfm-50` v1.0.0 and `mini-ipip-20` v1.0.0.

## Instruments

| | Comprehensive Discovery | Quick Discovery |
| --- | --- | --- |
| Instrument | IPIP Big-Five Factor Markers, 50 items | Mini-IPIP, 20 items |
| Authors | Lewis R. Goldberg; IPIP | Donnellan, Oswald, Baird & Lucas (2006), using IPIP items |
| Items per trait | 10 | 4 |
| Response scale | 1 Very inaccurate … 5 Very accurate | same |
| Intended population | Adults; English-speaking | same |
| Licence | Public domain (see ASSESSMENT_LICENSES.md) | same |

Traits: Extraversion, Agreeableness, Conscientiousness, Emotional Stability, Openness (the IPIP label is Intellect/Imagination). The Mini-IPIP's Neuroticism items are keyed toward Emotional Stability here so both instruments report the same direction; this reverses the sign and changes no information.

## Scoring (deterministic)

1. Validate: integer answers within 1–5, known items only.
2. Reverse minus-keyed items: `6 − answer`.
3. Per trait, require a minimum number of answered items: 8 of 10 (50-item) or 4 of 4 (20-item). Otherwise the trait is "insufficient" and the assessment cannot be completed.
4. Raw score = mean of the trait's answered items (prorated).
5. Display score = `(mean − 1) / 4 × 100`, rounded half-up to one decimal.
6. Band: lower (< 40), middle (40–60), higher (> 60). Bands describe position on the response scale, not relative to other people.
7. Negative Emotionality = 100 − Emotional Stability (presentation only).

Implemented in `services/backend/app/scoring/engine.py`; hand-computed expectations in `tests/test_scoring.py`. Using 1–5 scoring follows IPIP guidance so findings are comparable with published research.

## Why no percentiles

No reference population data is licensed or collected, so percentiles, rankings and "accuracy" figures are not shown (MASTER_PROMPT.md §17). Once a consenting, demographically described sample exists, norms can be computed and versioned separately.

## Response quality checks

- `uniform_responses`: 10+ answers, all identical.
- `rapid_completion`: completed in under 1.5 seconds per answered item (server-measured).

Flags are shown to the user and stored. They never change scores. Thresholds are heuristics, not validated cut-offs.

## Auditability

Each result stores: engine version, instrument id and version, SHA-256 of the instrument file, SHA-256 of the canonical answer set, archetype version and the full archetype ranking. Re-scoring the stored answers with the same versions must give identical output.

## Known limitations

- Self-report: affected by mood, self-perception and social desirability.
- The 20-item version has lower reliability than longer forms (Donnellan et al., 2006 report it as acceptable, not equivalent).
- Validity evidence comes from the source literature with mostly Western, English-speaking samples; it has not been re-established for this product's users.
- Translations will require forward/back translation and psychometric checks before use (SCIENTIFIC_VALIDATION_PLAN.md).

## References

- Goldberg, L. R. (1992). The development of markers for the Big-Five factor structure. *Psychological Assessment, 4*(1), 26–42.
- Goldberg, L. R., et al. (2006). The International Personality Item Pool and the future of public-domain personality measures. *Journal of Research in Personality, 40*, 84–96.
- Donnellan, M. B., Oswald, F. L., Baird, B. M., & Lucas, R. E. (2006). The Mini-IPIP scales. *Psychological Assessment, 18*(2), 192–203.
- IPIP website: https://ipip.ori.org/

## Version history

| Date | Change |
| --- | --- |
| 2026-11-26 | Engine 1.0.0; ipip-bfm-50 1.0.0; mini-ipip-20 1.0.0; archetypes 1.0.0 |
