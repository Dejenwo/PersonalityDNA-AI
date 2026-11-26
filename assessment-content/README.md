# Assessment content

Source of truth for assessment instruments, scoring rules and interpretation text. Content is **immutable per version**: the backend stores a SHA-256 of each loaded file and refuses to start if a file with an existing id and version has changed. To change content, add a new version file.

- `instruments/` — item banks (one JSON file per instrument version)
- `scoring-rules/` — scoring method, archetype mapping and trait interpretations
- `translations/` — reserved; translations require expert review (see docs/ASSESSMENT_METHODOLOGY.md)
- `licenses/` — licence record for every instrument
