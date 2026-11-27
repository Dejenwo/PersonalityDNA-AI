"""Administrative API. Each route needs a specific permission; unknown users and missing permissions both
look like 404 so the admin surface isn't advertised to other accounts."""

from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.admin.roles import Permission, Role
from app.admin.schemas import (
    AdminMe,
    AdminOrg,
    AdminOrgList,
    AuditList,
    ContentOverview,
    GrantIn,
    Health,
    LicenceIn,
    Metrics,
    RoleIn,
    StatusIn,
    UserDetail,
    UserList,
)
from app.admin.service import AdminService, roles_of, user_permissions
from app.api.deps import get_content, get_db
from app.api.errors import ApiError
from app.api.schemas import ErrorResponse
from app.assessments.content import ContentBundle
from app.auth.deps import CurrentUser
from app.database.models import User

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
Db = Annotated[Session, Depends(get_db)]
Content = Annotated[ContentBundle, Depends(get_content)]
CONFLICT: dict[int | str, dict[str, Any]] = {409: {"model": ErrorResponse}}


def admin_user(user: CurrentUser, db: Db) -> User:
    if user.email_verified_at is None or not roles_of(db, user.id):
        raise ApiError(404, "not_found", "Not found.")
    return user


Admin = Annotated[User, Depends(admin_user)]


def need(permission: Permission) -> Callable[..., User]:
    def dep(user: Admin, db: Db) -> User:
        if permission not in user_permissions(db, user):
            raise ApiError(404, "not_found", "Not found.")
        return user

    return dep


def get_admin(request: Request) -> AdminService:
    svc: AdminService = request.app.state.admin
    return svc


Svc = Annotated[AdminService, Depends(get_admin)]


@router.get("/me", response_model=AdminMe)
def me(user: Admin, db: Db) -> AdminMe:
    return AdminMe(roles=roles_of(db, user.id), permissions=sorted(user_permissions(db, user)))


@router.get("/users", response_model=UserList)
def find_users(
    db: Db,
    svc: Svc,
    _: Annotated[User, Depends(need("users.read"))],
    q: Annotated[str, Query(max_length=320)] = "",
) -> UserList:
    return svc.find_users(db, q)


@router.get("/users/{user_id}", response_model=UserDetail)
def user_detail(
    user_id: str, db: Db, svc: Svc, _: Annotated[User, Depends(need("users.read"))]
) -> UserDetail:
    return svc.user_detail(db, user_id)


@router.post("/users/{user_id}/status", response_model=UserDetail, responses=CONFLICT)
def set_status(
    user_id: str,
    body: StatusIn,
    request: Request,
    db: Db,
    svc: Svc,
    admin: Annotated[User, Depends(need("users.manage"))],
) -> UserDetail:
    """Disabling signs the account out everywhere. The reason is kept in the audit log."""
    return svc.set_status(db, admin, user_id, body.status, body.reason, request.app.state.auth)


@router.post("/users/{user_id}/grants", response_model=UserDetail)
def grant(
    user_id: str,
    body: GrantIn,
    db: Db,
    svc: Svc,
    admin: Annotated[User, Depends(need("subscriptions.manage"))],
) -> UserDetail:
    """Complimentary Premium for a fixed number of days (for example after a support issue). Doesn't renew."""
    return svc.grant(db, admin, user_id, body.plan_id, body.days, body.reason)


@router.delete("/users/{user_id}/grants/{subscription_id}", response_model=UserDetail, responses=CONFLICT)
def revoke_grant(
    user_id: str,
    subscription_id: str,
    db: Db,
    svc: Svc,
    admin: Annotated[User, Depends(need("subscriptions.manage"))],
) -> UserDetail:
    return svc.revoke_grant(db, admin, user_id, subscription_id)


@router.post("/users/{user_id}/roles", response_model=UserDetail, responses=CONFLICT)
def add_role(
    user_id: str, body: RoleIn, db: Db, svc: Svc, admin: Annotated[User, Depends(need("roles.manage"))]
) -> UserDetail:
    return svc.add_role(db, admin, user_id, body.role)


@router.delete("/users/{user_id}/roles/{role}", response_model=UserDetail, responses=CONFLICT)
def remove_role(
    user_id: str, role: Role, db: Db, svc: Svc, admin: Annotated[User, Depends(need("roles.manage"))]
) -> UserDetail:
    return svc.remove_role(db, admin, user_id, role)


@router.get("/organisations", response_model=AdminOrgList)
def find_orgs(
    db: Db,
    svc: Svc,
    _: Annotated[User, Depends(need("orgs.read"))],
    q: Annotated[str, Query(max_length=120)] = "",
) -> AdminOrgList:
    return svc.find_orgs(db, q)


@router.put("/organisations/{org_id}/licence", response_model=AdminOrg)
def set_licence(
    org_id: str, body: LicenceIn, db: Db, svc: Svc, admin: Annotated[User, Depends(need("orgs.manage"))]
) -> AdminOrg:
    """Record a seat licence agreed with the organisation. While active, its members get Premium features."""
    return svc.set_licence(db, admin, org_id, body.licence, body.seat_limit, body.days, body.reason)


@router.get("/metrics", response_model=Metrics)
def metrics(db: Db, svc: Svc, _: Annotated[User, Depends(need("metrics.read"))]) -> Metrics:
    return svc.metrics(db)


@router.get("/content", response_model=ContentOverview)
def content(
    request: Request, content: Content, svc: Svc, _: Annotated[User, Depends(need("content.read"))]
) -> ContentOverview:
    return svc.content(content, request.app.state.coach.prompt.label)


@router.get("/audit", response_model=AuditList)
def audit_log(
    db: Db,
    svc: Svc,
    _: Annotated[User, Depends(need("audit.read"))],
    before: datetime | None = None,
    event_type: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> AuditList:
    return svc.audit_log(db, before, event_type, limit)


@router.get("/health", response_model=Health)
def health(
    request: Request, db: Db, content: Content, svc: Svc, _: Annotated[User, Depends(need("health.read"))]
) -> Health:
    return svc.health(db, content, request.app.state.coach.provider.name)
