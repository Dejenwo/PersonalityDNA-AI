"""Rule-based safety checks around the coach. See docs/AI_SAFETY.md.

These rules are a floor, not the whole defence: the system prompt carries the same rules for the model,
and the evaluation suite in ai/evaluations measures both together. Rules favour recall for crisis
language (a false positive shows support resources; a miss is worse) and precision for output
retraction (so correct refusals such as "I can't tell whether you have ADHD" are not removed).
"""

import re
from dataclasses import dataclass, field

from app.coaching.context import CoachFacts

MAX_MESSAGE_CHARS = 4000


def _normalise(text: str) -> str:
    text = text.replace("\u2019", "'").replace("\u2018", "'")
    return re.sub(r"\s+", " ", text).strip().lower()


def _rx(*patterns: str) -> list[re.Pattern[str]]:
    return [re.compile(p) for p in patterns]


_FAMILY = r"(?:wife|husband|partner|boss|kids?|child|children|son|daughter|mother|father|mom|mum|dad|ex)"

CRISIS_RULES: dict[str, list[re.Pattern[str]]] = {
    "self_harm": _rx(
        r"\b(?:kill|killing|hurt|hurting|harm|harming|cut|cutting) my ?self\b",
        r"\bsuicid(?:e|al)\b",
        r"\bend(?:ing)? (?:it all|my life|my own life)\b",
        r"\btake my (?:own )?life\b",
        r"\b(?:want|wanted|wanting|wish|wishing) (?:i was |i were |to be )?(?:to die|dead)\b",
        r"\bself[- ]?harm",
        r"\bno (?:reason|point) (?:to|in) (?:live|living|going on)\b",
        r"\bbetter off (?:dead|without me)\b",
        r"\boverdos(?:e|ing)\b",
        r"\b(?:took|taken|swallowed) (?:too many|a lot of|a bunch of|all (?:my|the)) "
        r"(?:pills|tablets|meds)\b",
        r"\bdon't want to (?:live|be alive|exist|wake up)\b",
    ),
    "harm_to_others": _rx(
        rf"\b(?:kill|shoot|stab|strangle) (?:him|her|them|someone|somebody|people|my {_FAMILY})\b",
        r"\b(?:want|going|plan|planning) to (?:hurt|harm) (?:someone|somebody|people)\b",
        r"\b(?:want|going|plan|planning) to kill (?:someone|somebody|people|him|her|them)\b",
    ),
    "abuse": _rx(
        rf"\b(?:he|she|they|my {_FAMILY}) "
        r"(?:hits|hit|beats|beat|chokes|choked|strangles|strangled|kicks|kicked) me\b",
        r"\b(?:being|been|was|am|got) (?:abused|assaulted|raped)\b",
        r"\b(?:sexually )?(?:assaulted|raped|molested) me\b",
        r"\bdomestic (?:violence|abuse)\b",
        r"\bafraid for my (?:life|safety)\b",
    ),
}

INPUT_FLAG_RULES: dict[str, list[re.Pattern[str]]] = {
    "possible_prompt_injection": _rx(
        r"\bignore (?:all |any )?(?:the |your |my )?(?:previous|prior|above|earlier|system) "
        r"(?:instructions|rules|messages|prompts?)\b",
        r"\b(?:reveal|show|print|repeat|output|tell me) (?:me )?(?:your|the) (?:system |hidden |initial )?"
        r"(?:prompt|instructions|rules)\b",
        r"\bsystem prompt\b",
        r"\byou are now\b",
        r"\b(?:developer|dan|jailbreak|god|unrestricted) mode\b",
        r"</?(?:system|assistant|instructions)>",
    ),
    "other_user_data_request": _rx(
        r"\b(?:other|another) (?:user|person|member|account)'?s? "
        r"(?:results?|data|answers|scores|conversations?)\b",
        r"\b(?:results?|data|scores) (?:of|for) (?:other|another) (?:users?|people|members|accounts?)\b",
    ),
    "diagnosis_request": _rx(
        r"\b(?:do|might|could|can) i (?:have|be) (?:adhd|add|autism|autistic|depression|depressed|bipolar|"
        r"ocd|ptsd|anxiety|bpd|a personality disorder|narcissistic)\b",
        r"\bam i (?:a )?(?:autistic|depressed|bipolar|narcissist|narcissistic|psychopath|sociopath|"
        r"mentally ill)\b",
        r"\bdiagnos(?:e|is)\b",
        r"\b(?:mean|means|show|shows|suggest|suggests|prove|proves) (?:that )?i (?:have|am|'m) "
        r"(?:adhd|add|autism|autistic|depression|depressed|bipolar|ocd|ptsd|anxiety|bpd|narcissistic)\b",
        r"\bis (?:my \w+|he|she) (?:a |an )?(?:narcissist|psychopath|sociopath|bipolar|autistic)\b",
    ),
}

_CONDITIONS = (
    r"adhd|add|autism|asperger'?s|depression|clinical depression|bipolar(?: disorder)?|an anxiety disorder|"
    r"anxiety disorder|ocd|ptsd|borderline(?: personality disorder)?|bpd|narcissistic personality disorder|"
    r"npd|schizophrenia|a personality disorder|a mental (?:illness|disorder)"
)
# Words shortly before a match that turn it into a refusal or a hedge rather than a claim.
_NEGATION = re.compile(r"\b(?:not|n't|whether|if|cannot|can't|unable|no way|only a|don't know)\b")

OUTPUT_BLOCK_RULES: dict[str, list[re.Pattern[str]]] = {
    "diagnosis": _rx(
        rf"\byou (?:probably |likely |may |might |clearly |definitely |seem to |appear to )?"
        rf"(?:have|suffer from|are showing signs of|show signs of) (?:{_CONDITIONS})\b",
        r"\byou(?:'re| are) (?:a |an )?(?:narcissist|psychopath|sociopath|bipolar|autistic|clinically \w+|"
        r"mentally ill)\b",
        r"\b(?:i|we) (?:can )?diagnose you\b",
        r"\bmy diagnosis\b",
    ),
    "professional_claim": _rx(
        r"\b(?:i am|i'm) (?:a |an |your )(?:licensed |certified |registered |clinical )?"
        r"(?:therapist|psychologist|psychiatrist|counsell?or|doctor|physician)\b",
        r"\bas (?:a|an) (?:licensed |certified |registered |clinical )?"
        r"(?:therapist|psychologist|psychiatrist|counsell?or|doctor|physician),? (?:i|my)\b",
    ),
    "percentile_claim": _rx(
        r"\b\d{1,2}(?:st|nd|rd|th) percentile\b",
        r"\bpercentile (?:rank|of \d)",
        r"\btop \d{1,2} ?(?:%|percent\b)",
        r"\b(?:higher|lower|more|less) than \d{1,3} ?(?:%|percent) of "
        r"(?:people|users|the population|others)\b",
    ),
    "outcome_prediction": _rx(
        r"\byour (?:relationship|marriage) (?:will|is going to) (?:fail|succeed|last|end)\b",
        r"\byou (?:would|will) (?:make|be) (?:a )?(?:great|good|bad|poor|terrible|ideal) "
        r"(?:hire|employee|candidate|partner|husband|wife|spouse)\b",
    ),
}

_SCORE_NEAR_TRAIT = re.compile(
    r"\b(openness|conscientiousness|extraversion|agreeableness|emotional stability|negative emotionality)"
    r"\b[^.\n\d]{0,30}?(\d{1,3}(?:\.\d+)?)(?!\d|\.\d)(?!\s*(?:%|percent|st|nd|rd|th|items|statements|questions))"
)


@dataclass(frozen=True)
class InputScreen:
    crisis: str | None
    flags: list[str] = field(default_factory=list)


def screen_input(text: str) -> InputScreen:
    norm = _normalise(text)
    crisis = next((cat for cat, rules in CRISIS_RULES.items() if any(r.search(norm) for r in rules)), None)
    flags = [name for name, rules in INPUT_FLAG_RULES.items() if any(r.search(norm) for r in rules)]
    if crisis:
        flags.insert(0, f"crisis:{crisis}")
    return InputScreen(crisis=crisis, flags=flags)


def blocked_output(text: str, canary: str | None) -> str | None:
    """Name of the first hard rule the text breaks, or None. Called on the growing reply while streaming."""
    if canary and canary.lower() in text.lower():
        return "prompt_leak"
    norm = _normalise(text)
    for name, rules in OUTPUT_BLOCK_RULES.items():
        for rule in rules:
            for m in rule.finditer(norm):
                before = norm[max(0, m.start() - 40) : m.start()]
                if name in ("diagnosis", "professional_claim") and _NEGATION.search(before):
                    continue
                return name
    return None


def grounding_flags(text: str, facts: CoachFacts) -> list[str]:
    """Soft check: scores the reply attributes to a trait must match the context exactly."""
    scores = facts.scores()
    norm = _normalise(text)
    for m in _SCORE_NEAR_TRAIT.finditer(norm):
        if norm[: m.start(2)].endswith(("out of ", "of ")) and m.group(2) == "100":
            continue  # "out of 100" names the scale, not a score
        actual = scores.get(m.group(1))
        if actual is None or abs(actual - float(m.group(2))) > 0.05:
            return ["ungrounded_score"]
    return []


CRISIS_RESPONSE = """I'm really sorry you're dealing with this, and I'm glad you said something. What you've \
described sounds serious, and it's more than a personality coach should handle. You deserve support from a \
person who can help right now.

- If you or anyone else is in immediate danger, call your local emergency number now.
- In the US or Canada, you can call or text 988 to reach a crisis line.
- In the UK or Ireland, you can call Samaritans free on 116 123.
- Anywhere else, findahelpline.com lists free, confidential helplines in your country.

If you can, reach out to someone you trust and tell them how you're feeling. I'm here to talk about \
everyday things whenever you're ready."""

SAFETY_REPLACEMENT = """I started to write a reply that doesn't meet PersonalityDNA's safety rules, so I've \
removed it. I can't diagnose conditions, compare you with other people, predict outcomes or speak as a \
licensed professional. Could you tell me a bit more about the everyday situation you'd like help with?"""

REFUSAL_REPLACEMENT = """I can't help with that one. Is there something about your results or an everyday \
situation I can help with instead?"""
