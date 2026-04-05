"""Presentation helpers for research items (dashboard, feeds, detail)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import EvidenceStage, ResearchItem, ResearchItemAI, Trial

EVIDENCE_STAGE_LABELS: dict[EvidenceStage, str] = {
    EvidenceStage.BASIC_RESEARCH: "Basic research",
    EvidenceStage.ANIMAL_PRECLINICAL: "Animal / preclinical",
    EvidenceStage.EARLY_HUMAN: "Early human study",
    EvidenceStage.PHASE_1: "Phase 1",
    EvidenceStage.PHASE_2: "Phase 2",
    EvidenceStage.PHASE_3: "Phase 3",
    EvidenceStage.RESULTS_POSTED: "Results posted",
    EvidenceStage.REGULATORY_REVIEW: "Regulatory review",
    EvidenceStage.APPROVED: "Approved / guideline-impacting",
}

EVIDENCE_STAGE_LABELS_HE: dict[EvidenceStage, str] = {
    EvidenceStage.BASIC_RESEARCH: "מחקר בסיסי",
    EvidenceStage.ANIMAL_PRECLINICAL: "מודל חי / טרום־קליני",
    EvidenceStage.EARLY_HUMAN: "מחקר אנושי מוקדם",
    EvidenceStage.PHASE_1: "שלב 1",
    EvidenceStage.PHASE_2: "שלב 2",
    EvidenceStage.PHASE_3: "שלב 3",
    EvidenceStage.RESULTS_POSTED: "תוצאות פורסמו",
    EvidenceStage.REGULATORY_REVIEW: "ביקורת רגולטורית",
    EvidenceStage.APPROVED: "מאושר / משפיע על קווים מנחים",
}

_PLACEHOLDER_WHY_EN_NO_AI_LONG = (
    "This text is taken from the source’s own abstract (often technical). "
    "After AI enrichment runs for this condition, we’ll show a shorter plain-language summary "
    "and a clearer ‘why it matters’ with evidence strength."
)
_PLACEHOLDER_WHY_HE_NO_AI_LONG = (
    "הטקסט מובא מהתקציר של המקור (לעיתים טכני). אחרי שיעבור עיבוד AI יוצגו כאן סיכום קצר בעברית "
    "והסבר ׳למה זה חשוב׳ עם חוזק הראיות."
)
_PLACEHOLDER_WHY_EN_NO_AI_SHORT = (
    "Right now we only show the title and metadata. Enrichment adds an easy-to-read summary, "
    "why the update might matter to patients and families, and how strong the evidence is."
)
_PLACEHOLDER_WHY_HE_NO_AI_SHORT = (
    "כרגע מוצגים רק הכותרת והמטא־דאטה. העשרת AI מוסיפה סיכום קריא, למה העדכון עשוי להיות חשוב "
    "למטופלים ולמשפחות, ומה חוזק הראיות."
)


def evidence_stage_heuristic(db: Session, item: ResearchItem) -> tuple[str, str]:
    if item.item_type == "paper":
        return ("basic_research", EVIDENCE_STAGE_LABELS[EvidenceStage.BASIC_RESEARCH])
    if item.item_type == "regulatory":
        return ("regulatory_review", EVIDENCE_STAGE_LABELS[EvidenceStage.REGULATORY_REVIEW])
    if item.item_type == "trial":
        t = db.scalar(select(Trial).where(Trial.research_item_id == item.id))
        phase = (t.phase or "").lower() if t else ""
        if "1" in phase:
            return ("phase_1", EVIDENCE_STAGE_LABELS[EvidenceStage.PHASE_1])
        if "2" in phase:
            return ("phase_2", EVIDENCE_STAGE_LABELS[EvidenceStage.PHASE_2])
        if "3" in phase:
            return ("phase_3", EVIDENCE_STAGE_LABELS[EvidenceStage.PHASE_3])
        return ("early_human_study", EVIDENCE_STAGE_LABELS[EvidenceStage.EARLY_HUMAN])
    return ("basic_research", EVIDENCE_STAGE_LABELS[EvidenceStage.BASIC_RESEARCH])


def evidence_stage_heuristic_he(db: Session, item: ResearchItem) -> tuple[str, str]:
    if item.item_type == "paper":
        return ("basic_research", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.BASIC_RESEARCH])
    if item.item_type == "regulatory":
        return ("regulatory_review", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.REGULATORY_REVIEW])
    if item.item_type == "trial":
        t = db.scalar(select(Trial).where(Trial.research_item_id == item.id))
        phase = (t.phase or "").lower() if t else ""
        if "1" in phase:
            return ("phase_1", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.PHASE_1])
        if "2" in phase:
            return ("phase_2", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.PHASE_2])
        if "3" in phase:
            return ("phase_3", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.PHASE_3])
        return ("early_human_study", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.EARLY_HUMAN])
    return ("basic_research", EVIDENCE_STAGE_LABELS_HE[EvidenceStage.BASIC_RESEARCH])


def serialize_research_item(db: Session, item: ResearchItem, *, locale: str = "en") -> dict:
    use_he = locale == "he"
    ai_row = db.scalar(select(ResearchItemAI).where(ResearchItemAI.research_item_id == item.id))
    recap_locale: str = "en"

    if ai_row:
        code = ai_row.evidence_stage.value
        label_en = EVIDENCE_STAGE_LABELS.get(ai_row.evidence_stage, code.replace("_", " ").title())
        label_he = EVIDENCE_STAGE_LABELS_HE.get(ai_row.evidence_stage, label_en)
        he_sum = (ai_row.lay_summary_he or "").strip()
        he_why = (ai_row.why_it_matters_he or "").strip()
        if use_he and he_sum and he_why:
            summary = he_sum
            why = he_why
            label = label_he
            recap_locale = "he"
        else:
            summary = ai_row.lay_summary or ""
            why = ai_row.why_it_matters or ""
            label = label_en if not use_he else label_he
            recap_locale = "en"
        confidence = ai_row.confidence_level
        applicability = ai_row.applicability_age_group
        hype = ai_row.hype_risk
    else:
        if use_he:
            code, label = evidence_stage_heuristic_he(db, item)
        else:
            code, label = evidence_stage_heuristic(db, item)
        abstract = (item.abstract_or_body or "").strip()
        if len(abstract) >= 120:
            snippet = abstract[:580]
            if len(abstract) > 580:
                snippet = snippet.rsplit(" ", 1)[0] + "…"
            summary = snippet
            why = _PLACEHOLDER_WHY_HE_NO_AI_LONG if use_he else _PLACEHOLDER_WHY_EN_NO_AI_LONG
        else:
            summary = (
                "רשומה אמיתית שאינדקסנו ממקור מהימן (למשל PubMed או ClinicalTrials.gov). "
                "פתחו את הקישור למטה לטקסט המלא. אחרי העשרת AI יופיע כאן סיכום בשפה פשוטה."
                if use_he
                else (
                    "This card is a real record we indexed from a trusted feed (for example PubMed or ClinicalTrials.gov). "
                    "Use the source link below to read the full entry. A plain-language summary will appear here after AI enrichment."
                )
            )
            why = _PLACEHOLDER_WHY_HE_NO_AI_SHORT if use_he else _PLACEHOLDER_WHY_EN_NO_AI_SHORT
        confidence = "pending"
        applicability = "both"
        hype = "hypothesis_generating_only"

    return {
        "id": str(item.id),
        "title": item.title,
        "source_url": item.source_url,
        "published_at": item.published_at,
        "item_type": item.item_type,
        "evidence_stage": code,
        "evidence_stage_label": label,
        "summary": summary,
        "why_it_matters": why,
        "confidence_level": confidence,
        "applicability_age_group": applicability,
        "hype_risk": hype,
        "recap_locale": recap_locale,
    }
