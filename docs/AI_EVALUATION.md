# AI evaluation

**Status: plan. The evaluation harness will be built in Phase 8, before the coach is exposed to users.**

## Suites (stored in `ai/evaluations/`)

| Suite | What it checks | Pass rule |
| --- | --- | --- |
| Grounding | Mentioned scores and archetypes match the context exactly | 100% |
| Hallucinated findings | Asks about traits not assessed; model must say it doesn't know | ≥ 98% |
| Safety/crisis | Crisis prompts route to resources | 100% |
| Diagnosis refusal | "Do I have ADHD/depression…" handled without diagnosis | 100% |
| Prompt injection | Instructions hidden in user text or retrieved docs are ignored | ≥ 98% |
| Privacy | Attempts to get other users' data or system prompt | 100% |
| Bias | Same scenario with varied names/genders/cultures gives equivalent advice | Reviewer-scored parity |
| Usefulness | Rubric-scored by reviewers and LLM-as-judge with spot checks | Track trend |
| Cost/latency | Tokens and p95 latency per turn | Within plan budget |

Runs on every prompt or model change in CI with the mock provider for structure, and nightly against real providers once keys exist (cost-capped).
