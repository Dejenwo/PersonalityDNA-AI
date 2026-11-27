from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class CardTrait(BaseModel):
    name: str
    band: Literal["lower", "middle", "higher"]


class Card(BaseModel):
    """What a public card shows: no name, no scores, no free text written by the user."""

    archetype: str | None
    summary: str | None
    traits: list[CardTrait]
    created_on: str
    note: str


class CreateCardIn(BaseModel):
    report_id: str
    include_archetype: bool = True
    include_traits: bool = True


class ShareCardOut(BaseModel):
    id: str
    report_id: str
    token: str
    created_at: datetime
    card: Card


class ShareCardList(BaseModel):
    cards: list[ShareCardOut]
