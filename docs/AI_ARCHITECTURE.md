# AI architecture

**Status: design. Nothing in this document is implemented yet (Phase 8).**

## Principles

- AI explains and coaches; the deterministic engine scores. The coach receives scores, never answers.
- Only data the user has authorized enters a prompt, and only what the task needs (minimization).
- Every response separates assessment findings, user-provided information and AI suggestions.
- Start with one orchestrated call per turn; add multi-agent routing only when evaluations show a measurable gain.

## Components

```
user message ─► Input guard ─► Context builder ─► Router ─► Specialist prompt ─► LLM provider
                (injection,     (authorized         (insight, career,           (Anthropic /
                 PII, crisis)    scores, goals,      relationship,               OpenAI / Mock)
                                 history if          leadership, growth)               │
                                 consented)                                            ▼
                                                                     Output guard ◄── structured response
                                                                     (claims, diagnosis, certainty,
                                                                      fabricated findings, privacy)
                                                                              │
                                                                       stream to client
```

- `LLMProvider` interface: `generate(messages, schema, limits) -> stream`. Implementations: `AnthropicProvider`, `OpenAIProvider`, `MockProvider` (deterministic, used in tests and when no key is configured).
- Prompts are versioned files in `ai/prompts/` with an id and version recorded on every AI message.
- Retrieval: a reviewed knowledge base in `ai/knowledge-base/` (Markdown with citations); pgvector only if keyword retrieval proves insufficient.
- Usage: per-user daily token allowance by plan; usage recorded per request with model, tokens, cost estimate and prompt version.
- Caching: only for non-personal content (e.g. trait explanations), never for personalized replies.

## Data sent to providers

Trait scores and bands, archetype ids, user-stated goals, and the current conversation. Never: raw answers, email, name, journal entries (unless the user explicitly attaches one), payment data. Provider choice and data-retention settings documented per provider before enabling.

## External dependencies

API keys for Anthropic and/or OpenAI, and a spending cap decided by the owner.
