"""LLM provider abstraction for the coach.

A provider turns a CoachRequest into a stream: zero or more text chunks followed by exactly one
Completion. Providers never see the database; the coaching service decides what goes in a request.
"""

import re
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Literal, Protocol

import anthropic
from anthropic.types import AssistantMessageParam, MessageParam, TextBlockParam, UserMessageParam

from app.coaching.context import CoachFacts
from app.core.config import Settings


@dataclass(frozen=True)
class Turn:
    role: Literal["user", "assistant"]
    content: str


@dataclass(frozen=True)
class CoachRequest:
    # Same for every user: safe to cache at the provider.
    system_instructions: str
    # Personal, per-conversation context. Never cached.
    system_context: str
    turns: list[Turn]
    max_tokens: int
    # Structured copy of the context, for providers that do not call a model (the stand-in).
    facts: CoachFacts = field(default_factory=lambda: CoachFacts())


@dataclass(frozen=True)
class Completion:
    # "end_turn", "max_tokens", "refusal" or another provider-specific reason.
    stop_reason: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0


class ProviderError(Exception):
    """The provider could not produce a reply. `retryable` tells the user whether to try again."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class LLMProvider(Protocol):
    name: str
    model: str

    def stream(self, request: CoachRequest) -> Iterator[str | Completion]: ...


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class MockProvider:
    """Deterministic stand-in. Calls no external service; replies only with facts from the context.

    Used in development, tests, end-to-end tests and demos, and clearly labelled as such to the user.
    """

    name = "mock"
    model = "pdna-stand-in-1"

    def __init__(self, delay_seconds: float = 0.0) -> None:
        self._delay = delay_seconds

    def reply(self, request: CoachRequest) -> str:
        from app.coaching.safety import screen_input  # local import: safety imports nothing from here

        facts = request.facts
        question = request.turns[-1].content.strip() if request.turns else ""
        quoted = question if len(question) <= 90 else question[:87].rstrip() + "..."
        parts = [
            "_Demo mode: this reply comes from PersonalityDNA's built-in stand-in, not an AI model._",
        ]
        flags = set(screen_input(question).flags)
        lowered = question.lower()
        fixed = None
        if "diagnosis_request" in flags or "medication" in lowered:
            fixed = (
                "A personality questionnaire can't answer questions about health conditions or treatment, "
                "and I can't diagnose. A qualified health professional, such as your doctor, can help with "
                "that. If it would help, we can talk about the everyday situations behind your question."
            )
        elif flags & {"possible_prompt_injection", "other_user_data_request"}:
            fixed = (
                "I can't help with that. I only use the results you've chosen to share with me, and I keep "
                "my instructions private. Shall we get back to your own goals?"
            )
        elif re.search(r"\b(?:therapist|psychologist|psychiatrist|counsell?or)\b", lowered):
            fixed = (
                "I'm an AI coach, not a therapist or any other licensed professional. I can help you "
                "reflect on your results and everyday situations, and a qualified professional can offer "
                "therapy if you'd like that."
            )
        if fixed:
            parts += [fixed, "What would you like to focus on next?"]
            return "\n\n".join(parts)
        scored = [t for t in facts.traits if t.score is not None]
        if scored and re.search(r"\b(?:scores?|compare)\b", lowered):
            listed = "\n".join(f"- {t.name}: {t.score_text} out of 100 ({t.band} band)" for t in scored)
            parts.append(f"**From your results**\n{listed}")
        elif scored:
            high = max(scored, key=lambda t: t.score or 0)
            low = min(scored, key=lambda t: t.score or 0)
            parts.append(
                "**From your results**\n"
                f"Your highest score is {high.name} at {high.score_text} out of 100 ({high.band} band), "
                f"and your lowest is {low.name} at {low.score_text} out of 100 ({low.band} band)."
            )
        else:
            parts.append(
                "**From your results**\n"
                "You haven't shared assessment results with me in this conversation, so I can't say "
                "anything about your traits yet."
            )
        if quoted:
            parts.append(f'**What you told me**\nYou asked: "{quoted}"')
        ideas = []
        if scored:
            high = max(scored, key=lambda t: t.score or 0)
            if high.growth:
                ideas.append(high.growth[0])
            low = min(scored, key=lambda t: t.score or 0)
            ideas.append(
                f"This week, notice one moment when your {low.name.lower()} shaped what you did, "
                "and write down one sentence about it."
            )
        else:
            ideas.append("Take an assessment so we can ground the conversation in your own answers.")
        parts.append("**Ideas to try**\n" + "\n".join(f"- {i}" for i in ideas))
        parts.append("What would you like to focus on next?")
        return "\n\n".join(parts)

    def stream(self, request: CoachRequest) -> Iterator[str | Completion]:
        text = self.reply(request)
        words = text.split(" ")
        for i, word in enumerate(words):
            if self._delay:
                time.sleep(self._delay)
            yield word if i == len(words) - 1 else word + " "
        prompt = request.system_instructions + request.system_context
        prompt += "".join(t.content for t in request.turns)
        yield Completion(
            stop_reason="end_turn",
            model=self.model,
            input_tokens=_estimate_tokens(prompt),
            output_tokens=_estimate_tokens(text),
        )


class AnthropicProvider:
    """Claude via the official Anthropic SDK, streamed.

    The shared instructions are marked for prompt caching; the personal context block that follows is
    not part of the cached prefix.
    """

    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        effort: Literal["low", "medium", "high"],
        timeout_seconds: float,
        client: anthropic.Anthropic | None = None,
    ) -> None:
        self.model = model
        self._effort: Literal["low", "medium", "high"] = effort
        self._client = client or anthropic.Anthropic(api_key=api_key, timeout=timeout_seconds, max_retries=2)

    def stream(self, request: CoachRequest) -> Iterator[str | Completion]:
        system: list[TextBlockParam] = [
            {"type": "text", "text": request.system_instructions, "cache_control": {"type": "ephemeral"}},
            {"type": "text", "text": request.system_context},
        ]
        messages: list[MessageParam] = [
            UserMessageParam(role="user", content=t.content)
            if t.role == "user"
            else AssistantMessageParam(role="assistant", content=t.content)
            for t in request.turns
        ]
        try:
            with self._client.messages.stream(
                model=self.model,
                max_tokens=request.max_tokens,
                system=system,
                messages=messages,
                output_config={"effort": self._effort},
            ) as stream:
                yield from stream.text_stream
                final = stream.get_final_message()
        except anthropic.RateLimitError as exc:
            raise ProviderError("The AI provider is busy.") from exc
        except anthropic.APIStatusError as exc:
            raise ProviderError(
                f"AI provider error {exc.status_code}", retryable=exc.status_code >= 500
            ) from exc
        except anthropic.APIConnectionError as exc:  # includes timeouts
            raise ProviderError("Could not reach the AI provider.") from exc
        usage = final.usage
        yield Completion(
            stop_reason=final.stop_reason or "end_turn",
            model=final.model,
            input_tokens=usage.input_tokens + (usage.cache_creation_input_tokens or 0),
            output_tokens=usage.output_tokens,
            cache_read_tokens=usage.cache_read_input_tokens or 0,
        )


def make_provider(settings: Settings) -> LLMProvider:
    if settings.coach_provider == "anthropic":
        assert settings.anthropic_api_key is not None  # enforced by Settings validation
        return AnthropicProvider(
            api_key=settings.anthropic_api_key.get_secret_value(),
            model=settings.coach_model,
            effort=settings.coach_effort,
            timeout_seconds=settings.coach_request_timeout_seconds,
        )
    return MockProvider()
