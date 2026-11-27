"""Private journal endpoints. Signed-in users only; every entry is scoped to its owner (others get 404).
There are no admin endpoints for journals, and entries are never sent to AI providers."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_content, get_db
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.journal.schemas import (
    DeleteAllIn,
    EntryIn,
    EntryList,
    EntryOut,
    EntryPatch,
    KindOut,
    PromptsOut,
    SearchIn,
    TagsOut,
)
from app.journal.service import JournalService, to_markdown

router = APIRouter(prefix="/api/v1/journal", tags=["journal"], responses={401: {"model": ErrorResponse}})
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
NOT_FOUND: dict[int | str, dict[str, Any]] = {404: {"model": ErrorResponse}}


def get_journal(request: Request) -> JournalService:
    return JournalService(request.app.state.cipher)


Journal = Annotated[JournalService, Depends(get_journal)]


@router.get("/prompts", response_model=PromptsOut, responses={401: {}})
def prompts(content: Content) -> PromptsOut:
    """Prompts and the mood scale. Public: they contain no personal data."""
    j = content.journal.data
    return PromptsOut(
        note=j.note,
        support_note=j.support_note,
        mood_scale=list(j.mood_scale),
        kinds=[
            KindOut(id=k, label=v.label, description=v.description, prompts=list(v.prompts))
            for k, v in j.kinds.items()
        ],
    )


@router.get("/entries", response_model=EntryList)
def list_entries(
    user: CurrentUser,
    db: Db,
    journal: Journal,
    cursor: Annotated[str | None, Query(max_length=32)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> EntryList:
    return journal.page(db, user, cursor, limit)


@router.post("/entries", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(body: EntryIn, user: CurrentUser, db: Db, journal: Journal) -> EntryOut:
    return journal.create(db, user, body)


@router.post("/search", response_model=EntryList)
def search(body: SearchIn, user: CurrentUser, db: Db, journal: Journal) -> EntryList:
    return journal.search(db, user, body)


@router.get("/tags", response_model=TagsOut)
def tags(user: CurrentUser, db: Db, journal: Journal) -> TagsOut:
    return TagsOut(tags=journal.tags(db, user))


@router.get(
    "/export",
    responses={200: {"content": {"text/markdown": {}, "application/json": {}}}},
    response_class=Response,
)
def export(
    user: CurrentUser,
    db: Db,
    journal: Journal,
    content: Content,
    format: Literal["markdown", "json"] = "markdown",
) -> Response:
    """Downloads every entry, decrypted, as Markdown or JSON."""
    entries = journal.all_entries(db, user)
    if format == "json":
        payload = "[" + ",".join(e.model_dump_json() for e in entries) + "]"
        media, ext = "application/json", "json"
    else:
        j = content.journal.data
        payload = to_markdown(entries, {k: v.label for k, v in j.kinds.items()}, list(j.mood_scale))
        media, ext = "text/markdown; charset=utf-8", "md"
    return Response(
        payload,
        media_type=media,
        headers={
            "Content-Disposition": f'attachment; filename="journal.{ext}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/entries/{entry_id}", response_model=EntryOut, responses=NOT_FOUND)
def get_entry(entry_id: str, user: CurrentUser, db: Db, journal: Journal) -> EntryOut:
    return journal.out(journal.get(db, user, entry_id))


@router.patch("/entries/{entry_id}", response_model=EntryOut, responses=NOT_FOUND)
def update_entry(entry_id: str, body: EntryPatch, user: CurrentUser, db: Db, journal: Journal) -> EntryOut:
    return journal.update(db, user, entry_id, body)


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    responses=NOT_FOUND,
)
def delete_entry(entry_id: str, user: CurrentUser, db: Db, journal: Journal) -> Response:
    journal.delete(db, user, entry_id)
    return Response(status_code=204)


@router.post("/delete-all", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_all(body: DeleteAllIn, user: CurrentUser, db: Db, journal: Journal) -> Response:
    """Deletes every journal entry. The body must be {"confirm": true}."""
    journal.delete_all(db, user)
    return Response(status_code=204)
