from __future__ import annotations

import json
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from openai import OpenAI
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import (
    Condition,
    Digest,
    EvidenceStage,
    NotificationPreference,
    ResearchItem,
    ResearchItemAI,
    User,
    UserFollowedCondition,
)
from app.schemas.condition_digest import ConditionDigestOut
from app.services.email import send_digest_email
from app.services.openai_json_schema import patch_json_schema_for_openai_strict

logger = logging.getLogger(__name__)

DIGEST_COOLDOWN_HOURS = {"daily": 20, "weekly": 6 * 24, "major": 20}
WINDOW_DAYS = {"daily": 1, "weekly": 7, "major": 7}


def _digest_schema_text_config() -> dict[str, Any]:
    schema = ConditionDigestOut.model_json_schema()
    patch_json_schema_for_openai_strict(schema)
    return {
        "format": {
            "type": "json_schema",
            "name": "ConditionDigestOut",
            "schema": schema,
            "strict": True,
        }
    }


def _allowed_item_types(pref: NotificationPreference) -> list[str]:
    types: list[str] = []
    if pref.notify_trials:
        types.append("trial")
    if pref.notify_papers:
        types.append("paper")
    if pref.notify_regulatory:
        types.append("regulatory")
    if pref.notify_foundation_news and "paper" not in types:
        types.append("paper")
    return types if types else ["paper", "trial", "regulatory"]


def _is_major_item(ai: ResearchItemAI | None) -> bool:
    if ai is None:
        return False
    if ai.actionability_score >= 0.55:
        return True
    stage = ai.evidence_stage
    return stage in (
        EvidenceStage.RESULTS_POSTED,
        EvidenceStage.REGULATORY_REVIEW,
        EvidenceStage.APPROVED,
    )


def _markdown_from_digest(out: ConditionDigestOut) -> str:
    lines: list[str] = [f"## {out.headline}", "", out.overview.strip(), ""]
    if out.items:
        lines.append("### Highlights")
        lines.append("")
        for i, it in enumerate(out.items, start=1):
            lines.extend(
                [
                    f"**{i}. {it.title}**",
                    f"- Source: {it.source_url}",
                    f"- What changed: {it.what_changed}",
                    f"- Why it matters: {it.why_it_matters}",
                    f"- Evidence strength: {it.evidence_strength}",
                    f"- Still uncertain: {it.uncertainty_note}",
                    "",
                ]
            )
    lines.extend(["### What is still uncertain", "", out.what_still_uncertain.strip(), ""])
    lines.append(
        "_Educational research summary only — not personal medical advice. Discuss with your clinician._"
    )
    return "\n".join(lines)


@dataclass
class DigestRunStats:
    generated: int
    skipped: int
    errors: int


class DigestService:
    def __init__(self, db: Session):
        self.db = db

    def _recent_digest_exists(self, user_id: UUID, condition_id: UUID, digest_type: str) -> bool:
        cooldown = timedelta(hours=DIGEST_COOLDOWN_HOURS.get(digest_type, 20))
        since = datetime.now(tz=timezone.utc) - cooldown
        row = self.db.scalar(
            select(Digest)
            .where(
                Digest.user_id == user_id,
                Digest.condition_id == condition_id,
                Digest.digest_type == digest_type,
                Digest.created_at >= since,
            )
            .order_by(Digest.created_at.desc())
            .limit(1)
        )
        return row is not None

    def _gather_items(
        self,
        condition_id: UUID,
        window_start: datetime,
        pref: NotificationPreference,
        digest_type: str,
    ) -> list[ResearchItem]:
        types = _allowed_item_types(pref)
        apply_major = digest_type == "major" or pref.notify_major_only

        q = (
            select(ResearchItem)
            .where(
                ResearchItem.condition_id == condition_id,
                ResearchItem.published_at >= window_start,
                ResearchItem.item_type.in_(types),
            )
            .order_by(ResearchItem.published_at.desc())
            .limit(40)
        )
        items = list(self.db.scalars(q).all())
        if not apply_major:
            return items[:20]

        out: list[ResearchItem] = []
        for item in items:
            ai = self.db.scalar(select(ResearchItemAI).where(ResearchItemAI.research_item_id == item.id))
            if _is_major_item(ai):
                out.append(item)
            if len(out) >= 15:
                break
        return out

    def _call_openai(self, condition: Condition, digest_type: str, items: list[ResearchItem]) -> ConditionDigestOut:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY not configured")

        client = OpenAI(api_key=settings.openai_api_key)
        lines: list[str] = []
        for item in items:
            ai = self.db.scalar(select(ResearchItemAI).where(ResearchItemAI.research_item_id == item.id))
            summary = (ai.lay_summary if ai else "") or (item.abstract_or_body or "")[:1200]
            lines.append(
                "\n".join(
                    [
                        f"ID: {item.id}",
                        f"Title: {item.title}",
                        f"URL: {item.source_url}",
                        f"Published: {item.published_at.isoformat() if item.published_at else ''}",
                        f"Type: {item.item_type}",
                        f"Summary: {summary}",
                    ]
                )
            )
        bundle = "\n\n---\n\n".join(lines) if lines else "(No new indexed items in this window.)"

        system = (
            "You are CureCompass digest writer for patients and caregivers. "
            "Summarize only the provided trusted research items for the named condition. "
            "Use simple language. Do not give personal medical advice or treatment changes. "
            "If there are no items, still write a calm overview explaining no major indexed updates in the period. "
            "Output ONLY JSON matching the schema."
        )
        user = (
            f"Digest type: {digest_type}\n"
            f"Condition: {condition.canonical_name}\n\n"
            f"Items:\n{bundle}"
        )

        resp = client.responses.create(
            model=settings.openai_responses_model,
            input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            text=_digest_schema_text_config(),
            timeout=120,
        )
        raw = getattr(resp, "output_text", None)
        if not raw:
            try:
                raw = resp.output[0].content[0].text  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                raise ValueError(f"No digest JSON from model: {exc}") from exc

        return ConditionDigestOut.model_validate(json.loads(raw))

    def generate_one(
        self,
        user: User,
        condition: Condition,
        pref: NotificationPreference,
        digest_type: str,
        *,
        force: bool = False,
        manual: bool = False,
    ) -> Digest | None:
        if pref.frequency == "off":
            return None

        if digest_type in ("daily", "weekly") and not manual:
            if pref.frequency == "real_time":
                return None
            if digest_type == "daily" and pref.frequency != "daily":
                return None
            if digest_type == "weekly" and pref.frequency != "weekly":
                return None

        if digest_type == "major":
            if not pref.notify_major_only and not manual:
                return None
            if not manual and pref.frequency != "real_time":
                return None

        if not pref.in_app_enabled and not pref.email_enabled:
            return None

        if not force and self._recent_digest_exists(user.id, condition.id, digest_type):
            return None

        window_days = WINDOW_DAYS[digest_type]
        window_start = datetime.now(tz=timezone.utc) - timedelta(days=window_days)
        items = self._gather_items(condition.id, window_start, pref, digest_type)

        try:
            parsed = self._call_openai(condition, digest_type, items)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Digest AI failed user=%s condition=%s: %s", user.id, condition.slug, exc)
            title = f"{condition.canonical_name} — {digest_type.title()} digest (draft)"
            body = (
                "## Digest temporarily unavailable\n\n"
                "We could not generate an AI summary right now. "
                "Please try again later or view latest updates on your dashboard.\n"
            )
            row = Digest(
                user_id=user.id,
                condition_id=condition.id,
                digest_type=digest_type,
                title=title,
                body_markdown=body,
                structured_json={"error": str(exc), "item_count": len(items)},
            )
            self.db.add(row)
            self.db.flush()
            if pref.email_enabled:
                try:
                    if send_digest_email(user.email, title, body):
                        row.delivered_at = datetime.now(tz=timezone.utc)
                except (OSError, smtplib.SMTPException):
                    logger.exception("Digest email failed after AI error path")
            return row

        title = parsed.headline[:255]
        body = _markdown_from_digest(parsed)
        payload = parsed.model_dump()

        row = Digest(
            user_id=user.id,
            condition_id=condition.id,
            digest_type=digest_type,
            title=title,
            body_markdown=body,
            structured_json=payload,
        )
        self.db.add(row)
        self.db.flush()

        if pref.email_enabled:
            try:
                if send_digest_email(user.email, title, body):
                    row.delivered_at = datetime.now(tz=timezone.utc)
            except (OSError, smtplib.SMTPException):
                logger.exception("Digest email failed user=%s", user.id)

        return row

    def run_scheduled(self, digest_type: str) -> DigestRunStats:
        stats = DigestRunStats(generated=0, skipped=0, errors=0)
        follows = self.db.scalars(select(UserFollowedCondition)).all()
        for follow in follows:
            user = self.db.get(User, follow.user_id)
            condition = self.db.get(Condition, follow.condition_id)
            if not user or not condition:
                continue
            pref = self.db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == follow.user_id,
                    NotificationPreference.condition_id == follow.condition_id,
                )
            )
            if not pref:
                stats.skipped += 1
                continue
            try:
                row = self.generate_one(user, condition, pref, digest_type, force=False, manual=False)
                if row:
                    stats.generated += 1
                else:
                    stats.skipped += 1
            except Exception:  # noqa: BLE001
                logger.exception("Scheduled digest failed follow=%s", follow.id)
                stats.errors += 1
        return stats

    def generate_for_user(
        self,
        user: User,
        digest_type: str,
        condition_slugs: list[str] | None,
        *,
        force: bool = True,
    ) -> list[Digest]:
        """If ``condition_slugs`` is None or empty, include every followed condition; else only slugs in the set."""
        want: set[str] | None = set(condition_slugs) if condition_slugs else None
        q = select(UserFollowedCondition).where(UserFollowedCondition.user_id == user.id)
        follows = list(self.db.scalars(q).all())
        out: list[Digest] = []
        for follow in follows:
            condition = self.db.get(Condition, follow.condition_id)
            if not condition:
                continue
            if want is not None and condition.slug not in want:
                continue
            pref = self.db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == user.id,
                    NotificationPreference.condition_id == condition.id,
                )
            )
            if not pref:
                continue
            row = self.generate_one(user, condition, pref, digest_type, force=force, manual=True)
            if row:
                out.append(row)
        return out
