"""Resolve a free-text condition name via DB match or OpenAI, then optionally create a Condition row."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

from openai import OpenAI
from pydantic import BaseModel, Field
from sqlalchemy import Text, cast, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import Condition
from app.services.openai_json_schema import patch_json_schema_for_openai_strict


def _norm_spaces(s: str) -> str:
    return " ".join(s.split()).strip()


def slugify(name: str) -> str:
    s = _norm_spaces(name).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    if len(s) > 200:
        s = s[:200].rstrip("-")
    return s or "condition"


class ConditionResolutionAI(BaseModel):
    """Structured output from OpenAI for medical condition resolution."""

    is_medical_condition: bool
    canonical_name_en: str = Field(description="Standard English disease or condition name used in medical literature")
    short_description_en: str
    short_description_he: str = Field(
        default="",
        description="Short Hebrew description of the same condition, or empty string if unsure",
    )
    rare_disease: bool
    extra_synonyms: list[str] = Field(default_factory=list, description="Alternate names including colloquial or Hebrew terms")


def _condition_ai_schema_config() -> dict:
    schema = ConditionResolutionAI.model_json_schema()
    patch_json_schema_for_openai_strict(schema)
    return {
        "format": {
            "type": "json_schema",
            "name": "ConditionResolutionAI",
            "schema": schema,
            "strict": True,
        }
    }


def find_existing_condition(db: Session, raw: str) -> Condition | None:
    """Match catalog entries by normalized name, slug, or search-hit exact normalized canonical."""
    n = _norm_spaces(raw)
    if len(n) < 2:
        return None

    row = db.scalar(select(Condition).where(func.lower(Condition.canonical_name) == n.lower()))
    if row:
        return row

    slug = slugify(n)
    row = db.scalar(select(Condition).where(Condition.slug == slug))
    if row:
        return row

    escaped = n.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"
    syn_blob = cast(Condition.synonyms, Text)
    stmt = (
        select(Condition)
        .where(
            or_(
                Condition.canonical_name.ilike(pattern, escape="\\"),
                Condition.slug.ilike(pattern, escape="\\"),
                Condition.description.ilike(pattern, escape="\\"),
                syn_blob.ilike(pattern, escape="\\"),
            )
        )
        .order_by(Condition.canonical_name.asc())
        .limit(50)
    )
    want = _norm_spaces(n).lower()
    for c in db.scalars(stmt).all():
        if _norm_spaces(c.canonical_name).lower() == want:
            return c
    return None


def _merge_synonyms(user_query: str, ai: ConditionResolutionAI) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for s in [user_query, ai.canonical_name_en, *ai.extra_synonyms]:
        t = _norm_spaces(s)
        if not t:
            continue
        key = t.lower()
        if key not in seen:
            seen.add(key)
            out.append(t)
    return out


def _description_for_row(ai: ConditionResolutionAI) -> str:
    en = _norm_spaces(ai.short_description_en)
    he = _norm_spaces(ai.short_description_he)
    if he:
        return f"{en}\n\n[HE] {he}"
    return en


def ensure_unique_slug(db: Session, base_slug: str) -> str:
    s = slugify(base_slug)
    if len(s) < 2:
        s = "condition"
    n = 0
    while True:
        candidate = s if n == 0 else f"{s}-{n}"
        if len(candidate) > 255:
            candidate = candidate[:255].rstrip("-")
        exists = db.scalar(select(Condition.id).where(Condition.slug == candidate))
        if not exists:
            return candidate
        n += 1


def resolve_with_openai(user_query: str, locale: str) -> ConditionResolutionAI:
    if not (settings.openai_api_key or "").strip():
        raise RuntimeError("OpenAI API key is not configured")

    lang_note = "The user interface locale is Hebrew; they may have typed Hebrew or transliterated terms." if locale == "he" else "The user interface locale is English."

    system = (
        "You are a medical nomenclature assistant for CureCompass, a research-tracking app. "
        "Given a user phrase, decide if it refers to a specific diagnosable disease or medical condition "
        "(including rare diseases and syndromes). "
        "Do NOT accept: vague symptoms alone without a named condition, procedures, medications, "
        "lifestyle topics, or non-medical text. "
        "Return the standard English name as used in PubMed/ICD/OMIM-style literature. "
        "Be precise: expand abbreviations to full names when that is the standard form (e.g. NF1 → Neurofibromatosis type 1). "
        + lang_note
    )
    user = f'User input: """{user_query}"""\nRespond with structured JSON only per schema.'

    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_responses_model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        text=_condition_ai_schema_config(),
        timeout=60,
    )
    raw = getattr(response, "output_text", None)
    if not raw:
        try:
            raw = response.output[0].content[0].text  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"OpenAI output parse failed: {exc}") from exc

    return ConditionResolutionAI.model_validate(json.loads(raw))


def create_condition_from_ai(db: Session, user_query: str, ai: ConditionResolutionAI) -> tuple[Condition, bool]:
    """Insert a new Condition or return an existing row if canonical name already exists. Second value: True if inserted."""
    canonical = _norm_spaces(ai.canonical_name_en)
    if not canonical:
        raise ValueError("Empty canonical name from model")

    dup = db.scalar(select(Condition).where(func.lower(Condition.canonical_name) == canonical.lower()))
    if dup:
        return dup, False

    slug = ensure_unique_slug(db, canonical)
    synonyms = _merge_synonyms(user_query, ai)
    desc = _description_for_row(ai)

    row = Condition(
        id=uuid.uuid4(),
        canonical_name=canonical[:255],
        slug=slug[:255],
        description=desc,
        synonyms=synonyms,
        rare_disease_flag=bool(ai.rare_disease),
    )
    db.add(row)
    db.flush()
    return row, True


def condition_to_brief(c: Condition) -> dict[str, Any]:
    return {
        "id": str(c.id),
        "canonical_name": c.canonical_name,
        "slug": c.slug,
        "description": c.description or "",
    }
