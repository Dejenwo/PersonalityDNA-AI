"""Renders a stored report as a PDF. Every chart value is also printed as text, so nothing depends on the
bars alone. Only the stored report body is used, so the same report always renders the same content."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    ListFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from app.reports.schemas import ReportBody

# Colours match the design tokens (light theme primary, border and muted text).
PRIMARY = colors.HexColor("#4338ca")
LINE = colors.HexColor("#e3e5ee")
MUTED = colors.HexColor("#4a5168")
BAND = {"lower": "Lower", "middle": "Middle", "higher": "Higher"}


class ScoreBar(Flowable):
    """A 0-100 bar with the middle band (40-60) shaded. Decorative: the score is printed next to it."""

    def __init__(self, score: float, width: float = 120 * mm, height: float = 4 * mm) -> None:
        super().__init__()
        self.score, self.width, self.height = max(0.0, min(100.0, score)), width, height

    def draw(self) -> None:
        c = self.canv
        c.setFillColor(LINE)
        c.roundRect(0, 0, self.width, self.height, self.height / 2, stroke=0, fill=1)
        c.setFillColor(colors.HexColor("#c4c0ea"))
        c.rect(self.width * 0.4, 0, self.width * 0.2, self.height, stroke=0, fill=1)
        c.setFillColor(PRIMARY)
        if self.score > 0:
            c.roundRect(0, 0, self.width * self.score / 100, self.height, self.height / 2, stroke=0, fill=1)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    body = ParagraphStyle("Body", parent=base["BodyText"], fontName="Helvetica", fontSize=10.5, leading=15)
    return {
        "title": ParagraphStyle(
            "T", parent=base["Title"], fontName="Helvetica-Bold", fontSize=24, alignment=TA_LEFT
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName="Helvetica-Bold", fontSize=16, spaceBefore=10
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, spaceBefore=6
        ),
        "body": body,
        "muted": ParagraphStyle("Muted", parent=body, textColor=MUTED, fontSize=9.5, leading=13),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(escape(text), style)


def _bullets(items: list[str], style: ParagraphStyle) -> ListFlowable:
    flowables: list[Flowable] = [_p(i, style) for i in items]
    return ListFlowable(flowables, bulletType="bullet", start="•", leftIndent=12)


def render_pdf(body: ReportBody, created_on: str) -> bytes:
    s = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="PersonalityDNA personality report",
        author="PersonalityDNA",
        subject="Self-reported personality profile",
        creator=f"PersonalityDNA report {body.report_version}",
        lang="en",
    )
    story: list[Flowable] = [
        _p("Your personality report", s["title"]),
        _p(f"Created {created_on} · report version {body.report_version}", s["muted"]),
        Spacer(1, 4 * mm),
        _p(body.note, s["body"]),
    ]

    if body.profile:
        story += [_p("Profile", s["h1"]), _p(body.profile.name, s["h2"]), _p(body.profile.summary, s["body"])]
        story.append(_p(f"Your second-closest pattern is {body.profile.secondary}.", s["body"]))
        if body.profile.weak_fit:
            story.append(
                _p(
                    "Your answers don't match any one pattern closely, so treat this as a loose fit.",
                    s["muted"],
                )
            )
        story.append(_p(body.profile.disclaimer, s["muted"]))

    story.append(_p("Big Five traits", s["h1"]))
    story.append(
        _p("Scores show where you sit on the response scale, 0 to 100. They are not percentiles.", s["muted"])
    )
    for t in body.traits:
        value = (
            f"{t.score:.0f} out of 100, {BAND[t.band]} band"
            if t.score is not None and t.band
            else "Not scored"
        )
        block: list[Flowable] = [_p(f"{t.name}: {value}", s["h2"])]
        if t.score is not None:
            block += [ScoreBar(t.score), Spacer(1, 2 * mm)]
        block.append(_p(t.description, s["muted"]))
        if t.summary:
            block.append(_p(t.summary, s["body"]))
        story.append(KeepTogether(block))

    if body.strengths:
        story += [_p("Strengths", s["h1"]), _bullets(body.strengths, s["body"])]
    if body.development:
        story += [_p("Development opportunities", s["h1"]), _bullets(body.development, s["body"])]

    comms = [t for t in body.traits if t.communication]
    if comms:
        story.append(_p("Communication preferences", s["h1"]))
        story.append(_bullets([f"{t.name}: {t.communication}" for t in comms], s["body"]))
        story.append(_p("Relationship communication", s["h1"]))
        story.append(_bullets([f"{t.name}: {t.relationships}" for t in comms if t.relationships], s["body"]))

    if body.interests:
        story.append(_p("Career interests", s["h1"]))
        if body.interests.code and body.interests.top:
            story.append(_p(f"Your interest code is {body.interests.code}.", s["body"]))
            story.append(
                _bullets(
                    [f"{a.name} ({a.count} of {a.total} activities): {a.short}" for a in body.interests.top],
                    s["body"],
                )
            )
            if body.interests.fields:
                story.append(_p("Fields to explore: " + ", ".join(body.interests.fields) + ".", s["body"]))
        else:
            story.append(
                _p("You didn't choose any activities, so there are no clear interest areas yet.", s["body"])
            )
        story.append(_p(body.interests.note, s["muted"]))

    if body.leadership:
        story.append(_p("Leadership preferences", s["h1"]))
        if body.leadership.even:
            story.append(_p("Your preferences are fairly even across the leadership areas.", s["body"]))
        else:
            story.append(_p("Most preferred: " + ", ".join(body.leadership.most_preferred) + ".", s["body"]))
            story.append(
                _p("Least preferred: " + ", ".join(body.leadership.least_preferred) + ".", s["body"])
            )
        story.append(_p(body.leadership.note, s["muted"]))

    story += [_p("Personal values", s["h1"]), _p(body.values_note, s["body"])]

    if body.plan:
        story.append(_p("Your development plan", s["h1"]))
        story.append(_bullets([f"{p.title}: {p.reason}" for p in body.plan], s["body"]))

    story += [PageBreak(), _p("Methodology", s["h1"])]
    for m in body.methodology:
        story.append(_p(f"{m.instrument_name} (version {m.instrument_version})", s["h2"]))
        story.append(_p(m.scoring_summary, s["body"]))
        if m.band_note:
            story.append(_p(m.band_note, s["muted"]))
        story.append(_p(m.attribution, s["muted"]))
        story.append(
            _p(
                f"Scoring engine {m.engine_version}; content {m.content_sha256[:12]}; "
                f"answers {m.answers_sha256[:12]}.",
                s["muted"],
            )
        )
    refs = sorted({r for m in body.methodology for r in m.references})
    if refs:
        story += [_p("Scientific references", s["h1"]), _bullets(refs, s["muted"])]
    lims = [*body.limitations, *dict.fromkeys(x for m in body.methodology for x in m.limitations)]
    story += [_p("Limitations", s["h1"]), _bullets(lims, s["body"])]
    story.append(Spacer(1, 4 * mm))
    story.append(_p(f"Report fingerprint: content {body.content_sha256[:16]}.", s["muted"]))

    doc.build(story)
    return buf.getvalue()
