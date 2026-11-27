from datetime import datetime

from pydantic import BaseModel

from app.api.schemas import ModuleSummaryOut


class ModuleListItem(ModuleSummaryOut):
    activities_total: int
    activities_done: int


class ModuleList(BaseModel):
    note: str
    modules: list[ModuleListItem]


class LessonOut(BaseModel):
    title: str
    text: str


class ActivityOut(BaseModel):
    id: str
    title: str
    steps: list[str]
    completed_at: datetime | None


class ModuleOut(ModuleSummaryOut):
    lessons: list[LessonOut]
    activities: list[ActivityOut]
    reflection: str
