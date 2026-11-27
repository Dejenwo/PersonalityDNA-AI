"""Builds the public card from a report, and draws it as an SVG. Pure functions."""

from xml.sax.saxutils import escape

from app.reports.schemas import ReportBody
from app.sharing.schemas import Card, CardTrait

CARD_NOTE = (
    "Self-reported personality tendencies from PersonalityDNA. Not a measure of ability, "
    "not a diagnosis and not for hiring decisions."
)
BAND = {"lower": "Lower", "middle": "Middle", "higher": "Higher"}
# Light theme design tokens (packages/design-tokens): primary, ink, muted ink, line, surface.
PRIMARY, INK, MUTED, LINE, SURFACE = "#4338ca", "#14182b", "#4a5168", "#e3e5ee", "#ffffff"


def build_card(body: ReportBody, created_on: str, include_archetype: bool, include_traits: bool) -> Card:
    archetype = body.profile if include_archetype else None
    traits = (
        [CardTrait(name=t.name, band=t.band) for t in body.traits if t.band is not None]
        if include_traits
        else []
    )
    return Card(
        archetype=archetype.name if archetype else None,
        summary=archetype.summary if archetype else None,
        traits=traits,
        created_on=created_on,
        note=CARD_NOTE,
    )


def _wrap(text: str, width: int) -> list[str]:
    lines: list[str] = []
    line = ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def render_svg(card: Card) -> str:
    """A 1200 x 630 image (the usual link-preview size) with a text alternative in <title> and <desc>."""
    title = card.archetype or "Personality traits"
    desc = "; ".join(f"{t.name}: {BAND[t.band]}" for t in card.traits)
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" '
        'role="img" aria-labelledby="t d">',
        f'<title id="t">{escape(title)}</title>',
        f'<desc id="d">{escape(" ".join(x for x in (card.summary, desc, card.note) if x))}</desc>',
        f'<rect width="1200" height="630" fill="{SURFACE}"/>',
        f'<rect x="0" y="0" width="1200" height="12" fill="{PRIMARY}"/>',
        '<g font-family="Helvetica, Arial, sans-serif">',
        f'<text x="64" y="96" font-size="26" fill="{MUTED}">PersonalityDNA</text>',
        f'<text x="64" y="160" font-size="56" font-weight="700" fill="{INK}">{escape(title)}</text>',
    ]
    y = 210
    if card.summary:
        for line in _wrap(card.summary, 64)[:3]:
            parts.append(f'<text x="64" y="{y}" font-size="26" fill="{INK}">{escape(line)}</text>')
            y += 36
    y += 20
    for t in card.traits[:5]:
        x = {"lower": 0, "middle": 1, "higher": 2}[t.band]
        parts.append(f'<text x="64" y="{y + 22}" font-size="24" fill="{INK}">{escape(t.name)}</text>')
        for i in range(3):
            fill = PRIMARY if i == x else LINE
            parts.append(f'<rect x="{420 + i * 130}" y="{y}" width="120" height="28" rx="14" fill="{fill}"/>')
        parts.append(f'<text x="830" y="{y + 22}" font-size="22" fill="{MUTED}">{BAND[t.band]}</text>')
        y += 44
    for i, line in enumerate(_wrap(card.note, 100)[:2]):
        parts.append(f'<text x="64" y="{570 + i * 28}" font-size="20" fill="{MUTED}">{escape(line)}</text>')
    parts += ["</g>", "</svg>"]
    return "\n".join(parts)
