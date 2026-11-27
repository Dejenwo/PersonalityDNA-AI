"""Admin queries and actions. Every action is audited. Nothing here reads encrypted fields, answers,
journals, coaching messages or report bodies."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, distinct, func, select, text
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.admin.roles import permissions
from app.admin.schemas import (
    AdminOrg,
    AdminOrgList,
    AdminSubscription,
    AuditItem,
    AuditList,
    ContentFile,
    ContentOverview,
    CountWindow,
    Health,
    InstrumentInfo,
    Metrics,
    UserDetail,
    UserList,
    UserSummary,
)
from app.api.errors import ApiError
from app.assessments.content import ContentBundle
from app.billing.entitlements import Entitlements, is_current
from app.billing.webhooks import upsert
from app.core.config import Settings
from app.database.models import (
    AdminRole,
    AiUsageRecord,
    AssessmentResult,
    AssessmentSession,
    AuditEvent,
    Goal,
    GrowthEnrollment,
    Habit,
    JournalEntry,
    Organization,
    OrgMember,
    RelationshipLink,
    Report,
    ShareCard,
    Subscription,
    User,
)
from app.reports.builder import REPORT_VERSION
from app.scoring.engine import ENGINE_VERSION

REVENUE_NOTE = (
    "List prices of current paid subscriptions (annual divided by 12), before tax, store and payment fees, "
    "refunds and discounts. Support grants and development checkouts are excluded."
)
COST_NOTE = (
    "Estimated from token counts and the prices set in PDNA_AI_COST_*_USD_PER_MTOK. Check against the "
    "provider's invoice. The stand-in provider costs nothing and is excluded."
)
COST_UNSET_NOTE = (
    "Set PDNA_AI_COST_INPUT_USD_PER_MTOK and PDNA_AI_COST_OUTPUT_USD_PER_MTOK to see a cost estimate."
)


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(dt: datetime | None) -> datetime | None:
    return dt if dt is None or dt.tzinfo else dt.replace(tzinfo=UTC)


def audit(db: Session, admin: User, event: str, subject_id: str, **details: Any) -> None:
    db.add(
        AuditEvent(
            event_type=event,
            subject_type="user",
            subject_id=subject_id,
            details={"admin_id": str(admin.id), **details},
        )
    )


def roles_of(db: Session, user_id: uuid.UUID) -> list[str]:
    return sorted(db.scalars(select(AdminRole.role).where(AdminRole.user_id == user_id)))


def user_permissions(db: Session, user: User) -> set[str]:
    return permissions(roles_of(db, user.id))


class AdminService:
    def __init__(self, settings: Settings, entitlements: Entitlements) -> None:
        self.settings, self.entitlements = settings, entitlements

    # ---------- users ----------

    def _summary(self, db: Session, u: User) -> UserSummary:
        return UserSummary(
            id=str(u.id),
            email=u.email,
            created_at=_aware(u.created_at) or _now(),
            email_verified=u.email_verified_at is not None,
            status=u.status,
            plan_id=self.entitlements.plan(db, u.id).id,
        )

    def find_users(self, db: Session, q: str) -> UserList:
        """Exact id, or email containing the text. At most 25 results; an empty query lists the newest."""
        q = q.strip().lower()
        stmt = select(User).order_by(User.created_at.desc()).limit(25)
        if q:
            try:
                stmt = stmt.where(User.id == uuid.UUID(q))
            except ValueError:
                escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                stmt = stmt.where(User.email.like(f"%{escaped}%", escape="\\"))
        return UserList(users=[self._summary(db, u) for u in db.scalars(stmt)])

    def _user(self, db: Session, user_id: str) -> User:
        try:
            u = db.get(User, uuid.UUID(user_id))
        except ValueError:
            u = None
        if u is None:
            raise ApiError(404, "not_found", "Account not found.")
        return u

    def user_detail(self, db: Session, user_id: str) -> UserDetail:
        u = self._user(db, user_id)
        completed = db.scalar(
            select(func.count())
            .select_from(AssessmentSession)
            .where(AssessmentSession.user_id == u.id, AssessmentSession.status == "completed")
        )
        reports = db.scalar(select(func.count()).select_from(Report).where(Report.user_id == u.id))
        subs = db.scalars(
            select(Subscription).where(Subscription.user_id == u.id).order_by(Subscription.updated_at.desc())
        )
        return UserDetail(
            **self._summary(db, u).model_dump(),
            display_name=u.display_name,
            completed_assessments=completed or 0,
            reports=reports or 0,
            subscriptions=[
                AdminSubscription(
                    id=str(s.id),
                    provider=s.provider,
                    plan_id=s.plan_id,
                    status=s.status,
                    current_period_end=_aware(s.current_period_end),
                    cancel_at_period_end=s.cancel_at_period_end,
                )
                for s in subs
            ],
            admin_roles=roles_of(db, u.id),
        )

    def set_status(
        self, db: Session, admin: User, user_id: str, status: str, reason: str, auth: Any
    ) -> UserDetail:
        u = self._user(db, user_id)
        if u.id == admin.id:
            raise ApiError(409, "cannot_change_self", "You can't change your own account status.")
        if u.status != status:
            u.status = status
            if status == "disabled":
                auth.revoke_all(db, u.id)
            audit(db, admin, f"admin.user_{status}", str(u.id), reason=reason)
            db.commit()
        return self.user_detail(db, user_id)

    def grant(
        self, db: Session, admin: User, user_id: str, plan_id: str, days: int, reason: str
    ) -> UserDetail:
        u = self._user(db, user_id)
        if plan_id not in {p.id for p in self.entitlements.plans.paid()}:
            raise ApiError(404, "not_found", "Plan not found.")
        upsert(
            db,
            user=u,
            provider="manual",
            ref=f"manual-{uuid.uuid4()}",
            plan_id=plan_id,
            status="active",
            period_end=_now() + timedelta(days=days),
            cancel_at_period_end=True,
        )
        audit(db, admin, "admin.subscription_granted", str(u.id), plan_id=plan_id, days=days, reason=reason)
        db.commit()
        return self.user_detail(db, user_id)

    def revoke_grant(self, db: Session, admin: User, user_id: str, subscription_id: str) -> UserDetail:
        u = self._user(db, user_id)
        try:
            s = db.get(Subscription, uuid.UUID(subscription_id))
        except ValueError:
            s = None
        if s is None or s.user_id != u.id:
            raise ApiError(404, "not_found", "Subscription not found.")
        if s.provider != "manual":
            raise ApiError(
                409, "provider_managed", "Paid subscriptions are changed in Stripe or the app stores."
            )
        s.status, s.updated_at = "canceled", _now()
        audit(db, admin, "admin.subscription_revoked", str(u.id), subscription_id=str(s.id))
        db.commit()
        return self.user_detail(db, user_id)

    def add_role(self, db: Session, admin: User, user_id: str, role: str) -> UserDetail:
        u = self._user(db, user_id)
        if u.email_verified_at is None:
            raise ApiError(
                409, "email_unverified", "Only accounts with a confirmed email can hold admin roles."
            )
        if role not in roles_of(db, u.id):
            db.add(AdminRole(user_id=u.id, role=role, granted_by=admin.id, created_at=_now()))
            audit(db, admin, "admin.role_granted", str(u.id), role=role)
            db.commit()
        return self.user_detail(db, user_id)

    def remove_role(self, db: Session, admin: User, user_id: str, role: str) -> UserDetail:
        u = self._user(db, user_id)
        if u.id == admin.id and role == "superadmin":
            raise ApiError(409, "cannot_change_self", "Another superadmin must remove your superadmin role.")
        row = db.scalar(select(AdminRole).where(AdminRole.user_id == u.id, AdminRole.role == role))
        if row is not None:
            db.delete(row)
            audit(db, admin, "admin.role_removed", str(u.id), role=role)
            db.commit()
        return self.user_detail(db, user_id)

    # ---------- organisations ----------

    def _org(self, db: Session, org: Organization) -> AdminOrg:
        def count(*where: ColumnElement[bool]) -> int:
            return (
                db.scalar(
                    select(func.count()).select_from(OrgMember).where(OrgMember.org_id == org.id, *where)
                )
                or 0
            )

        until = _aware(org.licensed_until)
        return AdminOrg(
            id=str(org.id),
            name=org.name,
            members=count(),
            owners=count(OrgMember.role == "owner"),
            licence=org.licence,
            seat_limit=org.seat_limit,
            licensed_until=until,
            licence_active=org.licence == "licensed" and until is not None and until > _now(),
            created_at=_aware(org.created_at) or org.created_at,
        )

    def find_orgs(self, db: Session, q: str) -> AdminOrgList:
        stmt = select(Organization).order_by(Organization.created_at.desc()).limit(50)
        q = q.strip()
        if q:
            try:
                stmt = stmt.where(Organization.id == uuid.UUID(q))
            except ValueError:
                pattern = q.lower().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                stmt = stmt.where(func.lower(Organization.name).like(f"%{pattern}%", escape="\\"))
        return AdminOrgList(organisations=[self._org(db, o) for o in db.scalars(stmt)])

    def set_licence(
        self,
        db: Session,
        admin: User,
        org_id: str,
        licence: str,
        seat_limit: int,
        days: int | None,
        reason: str,
    ) -> AdminOrg:
        try:
            org = db.get(Organization, uuid.UUID(org_id))
        except ValueError:
            org = None
        if org is None:
            raise ApiError(404, "not_found", "Organisation not found.")
        if licence == "licensed" and days is None:
            raise ApiError(422, "days_required", "Give the licence length in days.")
        org.licence, org.seat_limit = licence, seat_limit
        org.licensed_until = _now() + timedelta(days=days) if licence == "licensed" and days else None
        audit(
            db,
            admin,
            "admin.org_licence",
            str(org.id),
            licence=licence,
            seat_limit=seat_limit,
            days=days,
            reason=reason,
        )
        db.commit()
        return self._org(db, org)

    # ---------- metrics ----------

    def metrics(self, db: Session) -> Metrics:
        now = _now()
        d7, d30 = now - timedelta(days=7), now - timedelta(days=30)

        def window(model: Any, column: Any, *where: ColumnElement[bool]) -> CountWindow:
            def count(*extra: ColumnElement[bool]) -> int:
                return db.scalar(select(func.count()).select_from(model).where(*where, *extra)) or 0

            return CountWindow(
                total=count(), last_7_days=count(column > d7), last_30_days=count(column > d30)
            )

        by_instrument = dict(
            db.execute(
                select(AssessmentResult.instrument_id, func.count()).group_by(AssessmentResult.instrument_id)
            ).all()
        )
        current = [s for s in db.scalars(select(Subscription)) if is_current(s, now)]
        by_plan: dict[str, int] = {}
        by_provider: dict[str, int] = {}
        mrr = 0
        for s in current:
            by_plan[s.plan_id] = by_plan.get(s.plan_id, 0) + 1
            by_provider[s.provider] = by_provider.get(s.provider, 0) + 1
            if s.provider in ("stripe", "revenuecat"):
                try:
                    plan = self.entitlements.plans.plan(s.plan_id)
                except KeyError:
                    continue
                mrr += plan.price_cents if plan.interval == "month" else round(plan.price_cents / 12)

        usage = db.execute(
            select(
                func.coalesce(func.sum(AiUsageRecord.input_tokens), 0),
                func.coalesce(func.sum(AiUsageRecord.output_tokens), 0),
                func.coalesce(func.sum(AiUsageRecord.cache_read_tokens), 0),
                func.count(distinct(AiUsageRecord.user_id)),
            ).where(AiUsageRecord.created_at > d30, AiUsageRecord.provider != "mock")
        ).one()
        tokens_in, tokens_out, cache_read, active = (int(x) for x in usage)
        cost = None
        pin, pout = self.settings.ai_cost_input_usd_per_mtok, self.settings.ai_cost_output_usd_per_mtok
        if pin is not None and pout is not None:
            cost = round((tokens_in * pin + tokens_out * pout) / 1_000_000, 2)

        def users_of(column: InstrumentedAttribute[uuid.UUID]) -> int:
            return db.scalar(select(func.count(distinct(column)))) or 0

        linked = db.scalar(
            select(func.count()).select_from(
                select(RelationshipLink.inviter_id.label("u"))
                .union(select(RelationshipLink.invitee_id.label("u")))
                .subquery()
            )
        )
        return Metrics(
            generated_at=now,
            users=window(User, User.created_at),
            verified_users=db.scalar(select(func.count()).where(User.email_verified_at.is_not(None))) or 0,
            disabled_users=db.scalar(select(func.count()).where(User.status == "disabled")) or 0,
            completed_assessments=window(
                AssessmentSession, AssessmentSession.completed_at, AssessmentSession.status == "completed"
            ),
            assessments_by_instrument={str(k): int(v) for k, v in by_instrument.items()},
            active_subscriptions_by_plan=by_plan,
            active_subscriptions_by_provider=by_provider,
            estimated_monthly_revenue_cents=mrr,
            revenue_note=REVENUE_NOTE,
            reports_created=window(Report, Report.created_at),
            active_share_cards=db.scalar(select(func.count()).select_from(ShareCard)) or 0,
            coach_turns=window(AiUsageRecord, AiUsageRecord.created_at),
            coach_tokens_30_days={"input": tokens_in, "output": tokens_out, "cache_read": cache_read},
            coach_cost_30_days_usd=cost,
            coach_cost_per_active_user_30_days_usd=round(cost / active, 4)
            if cost is not None and active
            else None,
            coach_active_users_30_days=active,
            cost_note=COST_NOTE if cost is not None else COST_UNSET_NOTE,
            feature_users={
                "journal": users_of(JournalEntry.user_id),
                "goals": users_of(Goal.user_id),
                "habits": users_of(Habit.user_id),
                "growth_programmes": users_of(GrowthEnrollment.user_id),
                "reports": users_of(Report.user_id),
                "relationships": linked or 0,
            },
        )

    # ---------- content, audit, health ----------

    def content(self, bundle: ContentBundle, coach_prompt: str) -> ContentOverview:
        files = [
            ContentFile(
                name=f.path.rsplit("/", 1)[-1], version=getattr(f.data, "version", "1"), sha256=f.sha256
            )
            for f in (
                bundle.archetypes,
                bundle.interpretations,
                bundle.interests,
                bundle.relationships,
                bundle.leadership,
                bundle.emotional_awareness,
                bundle.growth,
                bundle.journal,
                bundle.report,
            )
        ]
        return ContentOverview(
            engine_version=ENGINE_VERSION,
            report_version=REPORT_VERSION,
            coach_prompt=coach_prompt,
            plans_version=self.entitlements.plans.version,
            instruments=[
                InstrumentInfo(
                    id=i.data.id,
                    version=i.data.version,
                    name=i.data.name,
                    family=i.data.family,
                    tier=i.data.tier,
                    status=i.data.status,
                    items=len(i.data.items),
                    license=i.data.license.id,
                    references=list(i.data.references),
                    sha256=i.sha256,
                )
                for i in sorted(bundle.instruments.values(), key=lambda x: (x.data.id, x.data.version))
            ],
            files=files,
            note=(
                "Released content is immutable and changes only through a reviewed pull request that adds a "
                "new version file; the server refuses to start if a released file is edited. Drafts are "
                "hidden in production."
            ),
        )

    def audit_log(
        self, db: Session, before: datetime | None, event_type: str | None, limit: int
    ) -> AuditList:
        stmt = select(AuditEvent).order_by(AuditEvent.created_at.desc(), AuditEvent.id).limit(limit + 1)
        if before is not None:
            stmt = stmt.where(AuditEvent.created_at < before)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type.startswith(event_type, autoescape=True))
        rows = list(db.scalars(stmt))
        more = len(rows) > limit
        rows = rows[:limit]
        return AuditList(
            items=[
                AuditItem(
                    id=str(r.id),
                    event_type=r.event_type,
                    subject_type=r.subject_type,
                    subject_id=r.subject_id,
                    details=r.details or {},
                    created_at=_aware(r.created_at) or _now(),
                )
                for r in rows
            ],
            next_before=_aware(rows[-1].created_at) if more and rows else None,
        )

    def health(self, db: Session, bundle: ContentBundle, coach_provider: str) -> Health:
        try:
            db.execute(text("SELECT 1"))
            ok = True
        except Exception:  # noqa: BLE001 (report, don't raise)
            ok = False
        s = self.settings
        return Health(
            status="ok" if ok else "degraded",
            database=ok,
            environment=s.environment,
            coach_provider=coach_provider,
            coach_enabled=s.coach_enabled,
            email_provider=s.email_provider,
            billing_enforced=s.billing_enforce,
            stripe_configured=s.stripe_secret_key is not None and s.stripe_webhook_secret is not None,
            revenuecat_configured=s.revenuecat_webhook_auth is not None,
            content_instruments=len(bundle.instruments),
        )
