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
    family: Literal["big_five", "interests"] = "big_five"
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

    trait_ids = set(archetypes.traits)
    for inst_file in instruments.values():
        inst = inst_file.data
        scales = {s.id for s in inst.scales}
        expected_ids, what = (
            (trait_ids, "archetype traits")
            if inst.family == "big_five"
            else (set(interests.areas), "interest areas")
        )
        if scales != expected_ids:
            raise ContentError(f"{inst.id}: scales {scales} do not match {what}")
        expected_scoring = "likert_mean" if inst.family == "big_five" else "count_endorsed"
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
    )
