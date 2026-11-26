# AI architecture

**Status: implemented for the coach (Phase 8, ADR-011)**, with a deterministic stand-in provider by default and the Anthropic provider ready for a key. Not yet built: the router to specialist prompts (one prompt with a per-topic focus line is used instead), retrieval from `ai/knowledge-base/`, user goals in context, and an OpenAI provider.

Code: `services/backend/app/coaching/` (`providers.py`, `context.py`, `safety.py`, `service.py`, `routes.py`, `evaluation.py`). Prompt: `ai/prompts/coach.v1.md` (id and version recorded on every assistant message and usage record).

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

- `LLMProvider` interface: `stream(CoachRequest) -> text chunks, then one Completion` (stop reason, model, token counts). Implemented: `AnthropicProvider` (official SDK, streaming, `output_config.effort`, shared instructions cached, personal context uncached, typed errors mapped to retryable or not) and `MockProvider` (deterministic, labelled "demo mode"). `OpenAIProvider` is planned only if a second provider is wanted.
- Prompts are versioned files in `ai/prompts/` with an id and version recorded on every AI message.
- Retrieval: a reviewed knowledge base in `ai/knowledge-base/` (Markdown with citations); pgvector only if keyword retrieval proves insufficient.
- Usage: per-user daily token allowance by plan; usage recorded per request with model, tokens, cost estimate and prompt version.
- Caching: only for non-personal content (e.g. trait explanations), never for personalized replies.

## Data sent to providers

Trait scores and bands, archetype ids, user-stated goals, and the current conversation. Never: raw answers, email, name, journal entries (unless the user explicitly attaches one), payment data. Provider choice and data-retention settings documented per provider before enabling.

## External dependencies

API keys for Anthropic and/or OpenAI, and a spending cap decided by the owner.
