"""Public list of languages and their release status."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.i18n.locales import Locale, load_locales

router = APIRouter(prefix="/api/v1/locales", tags=["locales"])


class LocalesOut(BaseModel):
    default: str
    note: str
    locales: list[Locale]


@router.get("", response_model=LocalesOut)
def locales() -> LocalesOut:
    reg = load_locales()
    return LocalesOut(default=reg.default, note=reg.note, locales=reg.locales)
