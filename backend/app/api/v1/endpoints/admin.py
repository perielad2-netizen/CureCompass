from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_owner_admin_user
from app.db.session import get_db
from app.models.entities import (
    AdminJobRun,
    AskAIConversation,
    AskAIMessage,
    Digest,
    NotificationPreference,
    Source,
    User,
    UserFollowedCondition,
    UserPrivateDocument,
)
from app.schemas.admin_api import (
    AdminJobRunOut,
    AdminKpiTotalsOut,
    AdminReportsOut,
    AdminSourceOut,
    AdminSourcePatchIn,
    AdminUsageByUserOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/jobs", response_model=list[AdminJobRunOut])
def list_admin_jobs(
    db: Session = Depends(get_db),
    _: User = Depends(get_owner_admin_user),
    limit: int = Query(80, ge=1, le=200),
):
    rows = db.scalars(select(AdminJobRun).order_by(AdminJobRun.started_at.desc()).limit(limit)).all()
    return [
        AdminJobRunOut(
            id=str(r.id),
            job_type=r.job_type,
            status=r.status,
            payload_json=r.payload_json or {},
            output_json=r.output_json or {},
            error_text=r.error_text or "",
            started_at=r.started_at,
            finished_at=r.finished_at,
        )
        for r in rows
    ]


@router.get("/sources", response_model=list[AdminSourceOut])
def list_admin_sources(
    db: Session = Depends(get_db),
    _: User = Depends(get_owner_admin_user),
):
    rows = db.scalars(select(Source).order_by(Source.name)).all()
    return [
        AdminSourceOut(
            id=str(s.id),
            name=s.name,
            source_type=s.source_type,
            base_url=s.base_url,
            trust_score=s.trust_score,
            enabled=s.enabled,
        )
        for s in rows
    ]


@router.patch("/sources/{source_id}", response_model=AdminSourceOut)
def patch_admin_source(
    source_id: UUID,
    body: AdminSourcePatchIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_owner_admin_user),
):
    row = db.get(Source, source_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Source not found")
    row.enabled = body.enabled
    db.commit()
    db.refresh(row)
    return AdminSourceOut(
        id=str(row.id),
        name=row.name,
        source_type=row.source_type,
        base_url=row.base_url,
        trust_score=row.trust_score,
        enabled=row.enabled,
    )


@router.get("/reports", response_model=AdminReportsOut)
def get_admin_reports(
    db: Session = Depends(get_db),
    _: User = Depends(get_owner_admin_user),
    top_limit: int = Query(30, ge=1, le=200),
    recent_limit: int = Query(30, ge=1, le=200),
):
    now = datetime.now(tz=timezone.utc)
    cutoff_30d = now - timedelta(days=30)

    users_total = db.scalar(select(func.count()).select_from(User)) or 0
    admins_total = db.scalar(select(func.count()).select_from(User).where(User.is_admin.is_(True))) or 0
    users_created_30d = db.scalar(select(func.count()).select_from(User).where(User.created_at >= cutoff_30d)) or 0
    users_locale_he = db.scalar(select(func.count()).select_from(User).where(User.preferred_locale == "he")) or 0
    users_locale_en = db.scalar(select(func.count()).select_from(User).where(User.preferred_locale != "he")) or 0

    follows_total = db.scalar(select(func.count()).select_from(UserFollowedCondition)) or 0
    users_with_follows = (
        db.scalar(select(func.count(func.distinct(UserFollowedCondition.user_id))).select_from(UserFollowedCondition)) or 0
    )
    users_with_email_briefings_enabled = (
        db.scalar(
            select(func.count(func.distinct(NotificationPreference.user_id)))
            .select_from(NotificationPreference)
            .where(NotificationPreference.email_enabled.is_(True))
        )
        or 0
    )
    users_with_in_app_briefings_enabled = (
        db.scalar(
            select(func.count(func.distinct(NotificationPreference.user_id)))
            .select_from(NotificationPreference)
            .where(NotificationPreference.in_app_enabled.is_(True))
        )
        or 0
    )

    digests_total = db.scalar(select(func.count()).select_from(Digest)) or 0
    digests_delivered_total = db.scalar(select(func.count()).select_from(Digest).where(Digest.delivered_at.is_not(None))) or 0
    digest_users_total = db.scalar(select(func.count(func.distinct(Digest.user_id))).select_from(Digest)) or 0

    ask_ai_messages_total = db.scalar(select(func.count()).select_from(AskAIMessage)) or 0
    ask_ai_conversations_total = db.scalar(select(func.count()).select_from(AskAIConversation)) or 0
    ask_ai_users_total = (
        db.scalar(select(func.count(func.distinct(AskAIConversation.user_id))).select_from(AskAIConversation)) or 0
    )

    private_docs_total = db.scalar(select(func.count()).select_from(UserPrivateDocument)) or 0
    private_docs_processed = (
        db.scalar(
            select(func.count())
            .select_from(UserPrivateDocument)
            .where(UserPrivateDocument.processing_status == "processed")
        )
        or 0
    )

    follows_sq = (
        select(
            UserFollowedCondition.user_id.label("user_id"),
            func.count(UserFollowedCondition.id).label("followed_conditions"),
        )
        .group_by(UserFollowedCondition.user_id)
        .subquery()
    )
    conv_sq = (
        select(
            AskAIConversation.user_id.label("user_id"),
            func.count(AskAIConversation.id).label("ask_ai_conversations"),
        )
        .group_by(AskAIConversation.user_id)
        .subquery()
    )
    ai_msg_sq = (
        select(
            AskAIConversation.user_id.label("user_id"),
            func.count(AskAIMessage.id).label("ask_ai_messages"),
            func.max(AskAIMessage.created_at).label("last_ai_message_at"),
        )
        .join(AskAIConversation, AskAIConversation.id == AskAIMessage.conversation_id)
        .group_by(AskAIConversation.user_id)
        .subquery()
    )
    digest_sq = (
        select(
            Digest.user_id.label("user_id"),
            func.count(Digest.id).label("digests_created"),
            func.sum(case((Digest.delivered_at.is_not(None), 1), else_=0)).label("digests_delivered"),
            func.max(Digest.created_at).label("last_digest_at"),
        )
        .group_by(Digest.user_id)
        .subquery()
    )
    pref_sq = (
        select(
            NotificationPreference.user_id.label("user_id"),
            func.max(case((NotificationPreference.email_enabled.is_(True), 1), else_=0)).label(
                "has_email_briefings_enabled"
            ),
            func.max(case((NotificationPreference.in_app_enabled.is_(True), 1), else_=0)).label(
                "has_in_app_briefings_enabled"
            ),
        )
        .group_by(NotificationPreference.user_id)
        .subquery()
    )

    base_users = (
        select(
            User.id.label("user_id"),
            User.email,
            User.preferred_locale,
            User.created_at,
            func.coalesce(follows_sq.c.followed_conditions, 0).label("followed_conditions"),
            func.coalesce(ai_msg_sq.c.ask_ai_messages, 0).label("ask_ai_messages"),
            func.coalesce(conv_sq.c.ask_ai_conversations, 0).label("ask_ai_conversations"),
            func.coalesce(digest_sq.c.digests_created, 0).label("digests_created"),
            func.coalesce(digest_sq.c.digests_delivered, 0).label("digests_delivered"),
            func.coalesce(pref_sq.c.has_email_briefings_enabled, 0).label("has_email_briefings_enabled"),
            func.coalesce(pref_sq.c.has_in_app_briefings_enabled, 0).label("has_in_app_briefings_enabled"),
            ai_msg_sq.c.last_ai_message_at,
            digest_sq.c.last_digest_at,
        )
        .outerjoin(follows_sq, follows_sq.c.user_id == User.id)
        .outerjoin(conv_sq, conv_sq.c.user_id == User.id)
        .outerjoin(ai_msg_sq, ai_msg_sq.c.user_id == User.id)
        .outerjoin(digest_sq, digest_sq.c.user_id == User.id)
        .outerjoin(pref_sq, pref_sq.c.user_id == User.id)
    )

    top_rows = db.execute(
        base_users.order_by(
            func.coalesce(ai_msg_sq.c.ask_ai_messages, 0).desc(),
            func.coalesce(conv_sq.c.ask_ai_conversations, 0).desc(),
            User.created_at.desc(),
        ).limit(top_limit)
    ).mappings()
    recent_rows = db.execute(base_users.order_by(User.created_at.desc()).limit(recent_limit)).mappings()

    def _to_user_row(r: dict) -> AdminUsageByUserOut:
        return AdminUsageByUserOut(
            user_id=str(r["user_id"]),
            email=r["email"],
            preferred_locale=r["preferred_locale"] or "en",
            created_at=r["created_at"],
            followed_conditions=int(r["followed_conditions"] or 0),
            ask_ai_messages=int(r["ask_ai_messages"] or 0),
            ask_ai_conversations=int(r["ask_ai_conversations"] or 0),
            digests_created=int(r["digests_created"] or 0),
            digests_delivered=int(r["digests_delivered"] or 0),
            has_email_briefings_enabled=bool(r["has_email_briefings_enabled"]),
            has_in_app_briefings_enabled=bool(r["has_in_app_briefings_enabled"]),
            last_ai_message_at=r["last_ai_message_at"],
            last_digest_at=r["last_digest_at"],
        )

    return AdminReportsOut(
        generated_at=now,
        totals=AdminKpiTotalsOut(
            users_total=int(users_total),
            admins_total=int(admins_total),
            users_created_30d=int(users_created_30d),
            users_locale_he=int(users_locale_he),
            users_locale_en=int(users_locale_en),
            users_with_follows=int(users_with_follows),
            follows_total=int(follows_total),
            users_with_email_briefings_enabled=int(users_with_email_briefings_enabled),
            users_with_in_app_briefings_enabled=int(users_with_in_app_briefings_enabled),
            digests_total=int(digests_total),
            digests_delivered_total=int(digests_delivered_total),
            digest_users_total=int(digest_users_total),
            ask_ai_messages_total=int(ask_ai_messages_total),
            ask_ai_conversations_total=int(ask_ai_conversations_total),
            ask_ai_users_total=int(ask_ai_users_total),
            private_docs_total=int(private_docs_total),
            private_docs_processed=int(private_docs_processed),
        ),
        top_ai_users=[_to_user_row(r) for r in top_rows],
        recent_users=[_to_user_row(r) for r in recent_rows],
    )
