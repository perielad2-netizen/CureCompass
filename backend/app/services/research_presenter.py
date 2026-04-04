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


def serialize_research_item(db: Session, item: ResearchItem) -> dict:
    ai_row = db.scalar(select(ResearchItemAI).where(ResearchItemAI.research_item_id == item.id))
    if ai_row:
        code = ai_row.evidence_stage.value
        label = EVIDENCE_STAGE_LABELS.get(ai_row.evidence_stage, code.replace("_", " ").title())
        summary = ai_row.lay_summary or ""
        why = ai_row.why_it_matters or ""
        confidence = ai_row.confidence_level
        applicability = ai_row.applicability_age_group
        hype = ai_row.hype_risk
    else:
        code, label = evidence_stage_heuristic(db, item)
        abstract = (item.abstract_or_body or "").strip()
        # Ingestion stores the real abstract; show it until AI enrichment adds lay summaries.
        if len(abstract) >= 120:
            snippet = abstract[:580]
            if len(abstract) > 580:
                snippet = snippet.rsplit(" ", 1)[0] + "…"
            summary = snippet
            why = (
                "This text is taken from the source’s own abstract (often technical). "
                "After AI enrichment runs for this condition, we’ll show a shorter plain-language summary "
                "and a clearer ‘why it matters’ with evidence strength."
            )
        else:
            summary = (
                "This card is a real record we indexed from a trusted feed (for example PubMed or ClinicalTrials.gov). "
                "Use the source link below to read the full entry. A plain-language summary will appear here after AI enrichment."
            )
            why = (
                "Right now we only show the title and metadata. Enrichment adds an easy-to-read summary, "
                "why the update might matter to patients and families, and how strong the evidence is."
            )
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
    }
