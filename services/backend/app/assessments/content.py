"""Loading and validating version-controlled assessment content from assessment-content/."""

import hashlib
import json
from functools import cached_property
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ContentError(Exception):
    """Raised when assessment content is invalid or inconsistent."""


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ResponseLabel(_Frozen):
    value: int
    label: str


class ResponseScale(_Frozen):
    min: int = Field(ge=0)
    max: int = Field(le=7)
    labels: tuple[ResponseLabel, ...]

    @model_validator(mode="after")
    def _check(self) -> "ResponseScale":
        if self.max <= self.min:
            raise ValueError("response scale max must exceed min")
        if [lbl.value for lbl in self.labels] != list(range(self.min, self.max + 1)):
            raise ValueError("response labels must cover every value from min to max in order")
        return self


class ScaleDef(_Frozen):
    id: str
    name: str
    min_items_answered: int = Field(ge=1)


class Item(_Frozen):
    id: str
    number: int = Field(ge=1)
    text: str = Field(min_length=1)
    scale: str
    keyed: Literal["+", "-"]


class Source(_Frozen):
    name: str
    url: str
    authors: str


class LicenseRef(_Frozen):
    id: str
    file: str


class Instrument(_Frozen):
    schema_version: Literal[1]
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    # Draft instruments load only where drafts are enabled (development and tests) and may still change.
    status: Literal["released", "draft"] = "released"
    family: Literal["big_five", "interests", "leadership"] = "big_five"
    scoring: Literal["likert_mean", "count_endorsed"] = "likert_mean"
    name: str
    tier: Literal["quick", "comprehensive", "advanced"]
    locale: str
    estimated_minutes: int
    instructions: str
    response_scale: ResponseScale
    source: Source
    license: LicenseRef
    references: tuple[str, ...]
    scales: tuple[ScaleDef, ...]
    items: tuple[Item, ...]

    @model_validator(mode="after")
    def _check(self) -> "Instrument":
        scale_ids = [s.id for s in self.scales]
        if len(set(scale_ids)) != len(scale_ids):
            raise ValueError("duplicate scale ids")
        item_ids = [i.id for i in self.items]
        if len(set(item_ids)) != len(item_ids):
            raise ValueError("duplicate item ids")
        if [i.number for i in self.items] != list(range(1, len(self.items) + 1)):
            raise ValueError("item numbers must be 1..n in order")
        for item in self.items:
            if item.scale not in scale_ids:
                raise ValueError(f"item {item.id} references unknown scale {item.scale}")
        for scale in self.scales:
            n = sum(1 for i in self.items if i.scale == scale.id)
            if n == 0 or scale.min_items_answered > n:
                raise ValueError(f"scale {scale.id} has {n} items but needs {scale.min_items_answered}")
        return self

    @cached_property
    def items_by_id(self) -> dict[str, Item]:
        return {i.id: i for i in self.items}


class ArchetypeDef(_Frozen):
    id: str
    name: str
    prototype: dict[str, Literal[-1, 1]]
    summary: str
    strengths: tuple[str, ...]
    growth: tuple[str, ...]


class ArchetypeSet(_Frozen):
    id: str
    version: str
    status: str
    disclaimer: str
    method: str
    weak_fit_threshold: float
    traits: tuple[str, ...]
    archetypes: tuple[ArchetypeDef, ...]

    @model_validator(mode="after")
    def _check(self) -> "ArchetypeSet":
        protos = set()
        for a in self.archetypes:
            unknown = set(a.prototype) - set(self.traits)
            if unknown:
                raise ValueError(f"archetype {a.id} uses unknown traits {unknown}")
            key = tuple(a.prototype.get(t, 0) for t in self.traits)
            if key in protos:
                raise ValueError(f"archetype {a.id} duplicates another prototype")
            protos.add(key)
        return self


class BandText(_Frozen):
    summary: str
    strengths: tuple[str, ...]
    growth: tuple[str, ...]


class TraitText(_Frozen):
    name: str
    short: str
    bands: dict[Literal["lower", "middle", "higher"], BandText]


class Interpretations(_Frozen):
    id: str
    version: str
    locale: str
    note: str
    traits: dict[str, TraitText]


class InterestArea(_Frozen):
    name: str
    short: str
    enjoys: tuple[str, ...]
    fields: tuple[str, ...]
    reflection: str


class ExploreLink(_Frozen):
    label: str
    url: str


class InterestInterpretations(_Frozen):
    id: str
    version: str
    locale: str
    note: str
    explore_links: tuple[ExploreLink, ...]
    areas: dict[str, InterestArea]


class RelationshipTrait(_Frozen):
    poles: dict[Literal["higher", "lower"], str]
    shared: dict[Literal["higher", "middle", "lower"], str]
    complement: str
    misunderstanding: str
    prompt: str


class Exercise(_Frozen):
    title: str
    steps: tuple[str, ...]


class RelationshipInsights(_Frozen):
    id: str
    version: str
    locale: str
    note: str
    relation_types: dict[str, str]
    traits: dict[str, RelationshipTrait]
    exercises: tuple[Exercise, ...]
    shared_goals: tuple[str, ...]


class LeadershipArea(_Frozen):
    short: str
    preferred: str
    stretch: str
    module: str


class Lesson(_Frozen):
    title: str
    text: str


class Activity(_Frozen):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    steps: tuple[str, ...]


class LearningModule(_Frozen):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    area: str
    title: str
    summary: str
    lessons: tuple[Lesson, ...]
    activities: tuple[Activity, ...]
    reflection: str


class LearningTrack(_Frozen):
    """A set of learning modules with lessons, activities and a reflection question."""

    id: str = Field(pattern=r"^[a-z0-9-]+$")
    version: str
    locale: str
    title: str
    note: str
    support_note: str | None = None
    modules: tuple[LearningModule, ...]

    @model_validator(mode="after")
    def _check_modules(self) -> "LearningTrack":
        ids = [m.id for m in self.modules]
        if not ids or len(set(ids)) != len(ids):
            raise ValueError("a track needs modules with unique ids")
        for m in self.modules:
            acts = [a.id for a in m.activities]
            if not acts or len(set(acts)) != len(acts):
                raise ValueError(f"module {m.id} needs activities with unique ids")
        return self

    def module(self, module_id: str) -> LearningModule | None:
        return next((m for m in self.modules if m.id == module_id), None)


class LeadershipProgram(LearningTrack):
    areas: dict[str, LeadershipArea]

    @model_validator(mode="after")
    def _check_areas(self) -> "LeadershipProgram":
        ids = {m.id for m in self.modules}
        for m in self.modules:
            if m.area not in self.areas:
                raise ValueError(f"module {m.id} references unknown area {m.area}")
        for area_id, area in self.areas.items():
            if area.module not in ids:
                raise ValueError(f"area {area_id} references unknown module {area.module}")
        return self


class GrowthPractice(_Frozen):
    title: str
    steps: tuple[str, ...]


class GrowthWeek(_Frozen):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    topic: str
    title: str
    objective: str
    lesson: Lesson
    practice: GrowthPractice
    daily: tuple[str, ...] = Field(min_length=5, max_length=5)
    milestone: str
    self_evaluation: str
    reflection: str


class GrowthProgram(_Frozen):
    id: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str
    days: Literal[7, 30, 60, 90]
    weeks: tuple[str, ...] = Field(min_length=1)
    summary: str
    objectives: tuple[str, ...] = Field(min_length=1)


class GrowthAcademy(_Frozen):
    """Development programmes built from weekly units: each week is a lesson day, five exercise days and a
    milestone day with a self-evaluation. Days beyond the last full week are review days."""

    id: str
    version: str
    locale: str
    note: str
    self_evaluation_scale: tuple[str, str, str, str, str]
    review_days: tuple[str, ...]
    weeks: tuple[GrowthWeek, ...]
    programs: tuple[GrowthProgram, ...]

    @model_validator(mode="after")
    def _check(self) -> "GrowthAcademy":
        week_ids = [w.id for w in self.weeks]
        program_ids = [p.id for p in self.programs]
        if len(set(week_ids)) != len(week_ids) or len(set(program_ids)) != len(program_ids):
            raise ValueError("duplicate week or programme ids")
        for p in self.programs:
            unknown = set(p.weeks) - set(week_ids)
            if unknown:
                raise ValueError(f"programme {p.id} references unknown weeks {sorted(unknown)}")
            extra = p.days - 7 * len(p.weeks)
            if not 0 <= extra <= len(self.review_days):
                raise ValueError(f"programme {p.id}: {len(p.weeks)} weeks do not fit {p.days} days")
        return self

    def program(self, program_id: str) -> GrowthProgram | None:
        return next((p for p in self.programs if p.id == program_id), None)

    def week(self, week_id: str) -> GrowthWeek:
        return next(w for w in self.weeks if w.id == week_id)


JournalKind = Literal["daily", "gratitude", "goal", "development", "communication", "free"]


class JournalKindContent(_Frozen):
    label: str
    description: str
    prompts: tuple[str, ...] = Field(min_length=1)


class JournalPrompts(_Frozen):
    id: str
    version: str
    locale: str
    note: str
    support_note: str
    mood_scale: tuple[str, str, str, str, str]
    kinds: dict[JournalKind, JournalKindContent]

    @model_validator(mode="after")
    def _check(self) -> "JournalPrompts":
        if set(self.kinds) != {"daily", "gratitude", "goal", "development", "communication", "free"}:
            raise ValueError("journal prompts must cover every entry kind")
        return self


class LoadedFile[T: BaseModel](BaseModel):
    model_config = ConfigDict(frozen=True)
    data: T
    sha256: str
    path: str


class ContentBundle(BaseModel):
    model_config = ConfigDict(frozen=True)
    instruments: dict[str, LoadedFile[Instrument]]  # key: "id@version"
    archetypes: LoadedFile[ArchetypeSet]
    interpretations: LoadedFile[Interpretations]
    interests: LoadedFile[InterestInterpretations]
    relationships: LoadedFile[RelationshipInsights]
    leadership: LoadedFile[LeadershipProgram]
    emotional_awareness: LoadedFile[LearningTrack]
    growth: LoadedFile[GrowthAcademy]
    journal: LoadedFile[JournalPrompts]

    def track(self, track_id: str) -> LearningTrack | None:
        """Learning tracks by their public id; None for unknown ids."""
        tracks: dict[str, LearningTrack] = {
            "leadership": self.leadership.data,
            "emotional-awareness": self.emotional_awareness.data,
        }
        return tracks.get(track_id)

    def instrument(self, instrument_id: str, version: str) -> LoadedFile[Instrument]:
        try:
            return self.instruments[f"{instrument_id}@{version}"]
        except KeyError as exc:
            raise ContentError(f"unknown instrument {instrument_id}@{version}") from exc


def _read(path: Path) -> tuple[dict[str, object], str]:
    raw = path.read_bytes()
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def load_content(content_dir: Path, *, include_drafts: bool = True) -> ContentBundle:
    if not content_dir.is_dir():
        raise ContentError(f"content directory not found: {content_dir}")
    instruments: dict[str, LoadedFile[Instrument]] = {}
    for path in sorted((content_dir / "instruments").glob("*.json")):
        data, sha = _read(path)
        inst = Instrument.model_validate(data)
        if inst.status == "draft" and not include_drafts:
            continue
        expected = f"{inst.id}.v{inst.version}.json"
        if path.name != expected:
            raise ContentError(f"{path.name} must be named {expected}")
        if not (content_dir / inst.license.file).is_file():
            raise ContentError(f"{inst.id}: licence record {inst.license.file} is missing")
        instruments[f"{inst.id}@{inst.version}"] = LoadedFile[Instrument](
            data=inst, sha256=sha, path=str(path)
        )
    if not instruments:
        raise ContentError("no instruments found")

    arch_data, arch_sha = _read(content_dir / "scoring-rules" / "archetypes.v1.json")
    interp_data, interp_sha = _read(content_dir / "scoring-rules" / "trait-interpretations.v1.json")
    archetypes = ArchetypeSet.model_validate(arch_data)
    interpretations = Interpretations.model_validate(interp_data)
    interest_data, interest_sha = _read(content_dir / "scoring-rules" / "interest-interpretations.v1.json")
    interests = InterestInterpretations.model_validate(interest_data)
    rel_data, rel_sha = _read(content_dir / "scoring-rules" / "relationship-insights.v1.json")
    relationships = RelationshipInsights.model_validate(rel_data)
    lead_data, lead_sha = _read(content_dir / "scoring-rules" / "leadership-program.v1.json")
    leadership = LeadershipProgram.model_validate(lead_data)
    ea_data, ea_sha = _read(content_dir / "scoring-rules" / "emotional-awareness.v1.json")
    emotional_awareness = LearningTrack.model_validate(ea_data)
    growth_data, growth_sha = _read(content_dir / "scoring-rules" / "growth-academy.v1.json")
    growth = GrowthAcademy.model_validate(growth_data)
    journal_data, journal_sha = _read(content_dir / "scoring-rules" / "journal-prompts.v1.json")
    journal = JournalPrompts.model_validate(journal_data)

    trait_ids = set(archetypes.traits)
    for inst_file in instruments.values():
        inst = inst_file.data
        scales = {s.id for s in inst.scales}
        expected_ids, what = {
            "big_five": (trait_ids, "archetype traits"),
            "interests": (set(interests.areas), "interest areas"),
            "leadership": (set(leadership.areas), "leadership areas"),
        }[inst.family]
        if scales != expected_ids:
            raise ContentError(f"{inst.id}: scales {scales} do not match {what}")
        expected_scoring = "count_endorsed" if inst.family == "interests" else "likert_mean"
        if inst.scoring != expected_scoring:
            raise ContentError(f"{inst.id}: {inst.family} instruments use {expected_scoring} scoring")
    if set(interpretations.traits) != trait_ids:
        raise ContentError("trait interpretations do not cover exactly the archetype traits")
    if set(relationships.traits) != trait_ids:
        raise ContentError("relationship insights do not cover exactly the archetype traits")
    for t in relationships.traits.values():
        if set(t.poles) != {"higher", "lower"} or set(t.shared) != {"higher", "middle", "lower"}:
            raise ContentError("relationship insights need higher/lower poles and higher/middle/lower notes")

    return ContentBundle(
        instruments=instruments,
        archetypes=LoadedFile[ArchetypeSet](data=archetypes, sha256=arch_sha, path="archetypes.v1.json"),
        interpretations=LoadedFile[Interpretations](
            data=interpretations, sha256=interp_sha, path="trait-interpretations.v1.json"
        ),
        interests=LoadedFile[InterestInterpretations](
            data=interests, sha256=interest_sha, path="interest-interpretations.v1.json"
        ),
        relationships=LoadedFile[RelationshipInsights](
            data=relationships, sha256=rel_sha, path="relationship-insights.v1.json"
        ),
        leadership=LoadedFile[LeadershipProgram](
            data=leadership, sha256=lead_sha, path="leadership-program.v1.json"
        ),
        emotional_awareness=LoadedFile[LearningTrack](
            data=emotional_awareness, sha256=ea_sha, path="emotional-awareness.v1.json"
        ),
        growth=LoadedFile[GrowthAcademy](data=growth, sha256=growth_sha, path="growth-academy.v1.json"),
        journal=LoadedFile[JournalPrompts](data=journal, sha256=journal_sha, path="journal-prompts.v1.json"),
    )
