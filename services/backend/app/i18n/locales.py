"""Supported languages and their release status. English is the only released language; others move from
planned to in_review to released through the reviewed workflow in docs/LOCALIZATION.md."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Status = Literal["planned", "in_review", "released"]


class Locale(BaseModel):
    code: str = Field(pattern=r"^[a-z]{2,3}(-[A-Z][a-z]{3})?(-[A-Z]{2})?$")
    name: str
    native_name: str
    direction: Literal["ltr", "rtl"]
    status: Status


class LocaleRegistry(BaseModel):
    version: str
    default: str
    note: str
    locales: list[Locale]

    @model_validator(mode="after")
    def _check(self) -> "LocaleRegistry":
        codes = [x.code for x in self.locales]
        if len(set(codes)) != len(codes):
            raise ValueError("locale codes must be unique")
        default = self.get(self.default)
        if default is None or default.status != "released":
            raise ValueError("the default locale must be released")
        return self

    def get(self, code: str) -> Locale | None:
        return next((x for x in self.locales if x.code == code), None)

    def released(self) -> list[Locale]:
        return [x for x in self.locales if x.status == "released"]

    def negotiate(self, accept_language: str | None) -> str:
        """Best released locale for an Accept-Language header (by q-value, then order), else the default."""
        released = {x.code for x in self.released()}
        choices: list[tuple[float, int, str]] = []
        for i, part in enumerate((accept_language or "").split(",")):
            tag, _, params = part.strip().partition(";")
            q = 1.0
            if params.strip().startswith("q="):
                try:
                    q = float(params.strip()[2:])
                except ValueError:
                    q = 0.0
            if tag and q > 0:
                choices.append((-q, i, tag.strip()))
        for _, _, tag in sorted(choices):
            for candidate in (tag, tag.split("-")[0].lower()):
                if candidate in released:
                    return candidate
        return self.default


@lru_cache
def load_locales(path: Path = Path(__file__).with_name("locales.v1.json")) -> LocaleRegistry:
    return LocaleRegistry.model_validate(json.loads(path.read_text(encoding="utf-8")))
