"""Phase 3 aggregation: dedupe, merge, ranking (no DB)."""

from __future__ import annotations

from datetime import datetime, timezone
from app.schemas.medical_intel import NormalizedMedicalDocument
from app.services.medical_intel.aggregation import (
    aggregate_and_rank,
    canonical_url,
    composite_rank_score,
    dedupe_documents,
    format_aggregated_evidence_for_prompt,
    title_similarity,
)
from app.services.medical_intel.intent import UserIntent


def _doc(
    *,
    doc_id: str,
    title: str,
    url: str,
    source: str = "PubMed",
    entity: str = "research_paper",
    rel: float = 0.8,
    internal: str | None = "abc",
    raw: dict | None = None,
) -> NormalizedMedicalDocument:
    return NormalizedMedicalDocument(
        id=doc_id,
        entity_type=entity,  # type: ignore[arg-type]
        title=title,
        source_name=source,
        source_url=url,
        summary="Abstract text here.",
        plain_language_summary="",
        condition_name="NF1",
        reliability_score=0.96,
        relevance_score=rel,
        freshness_score=0.7,
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        raw_data=raw or {},
        internal_research_item_id=internal,
    )


def test_canonical_url_strips_www_and_fragment():
    a = canonical_url("HTTPS://WWW.Example.COM/path/?utm_source=x&a=1")
    b = canonical_url("https://example.com/path?a=1")
    assert a == b


def test_dedupe_by_canonical_url():
    d1 = _doc(doc_id="a", title="Paper A", url="https://pubmed.ncbi.nlm.nih.gov/123/")
    d2 = _doc(doc_id="b", title="Different title", url="https://pubmed.ncbi.nlm.nih.gov/123")
    kept, n = dedupe_documents([d1, d2])
    assert n == 1
    assert len(kept) == 1
    assert kept[0].id == "a"


def test_dedupe_by_fuzzy_title_same_entity():
    d1 = _doc(doc_id="x", title="Neurofibromatosis type 1: a review", url="https://a.example/p1")
    d2 = _doc(
        doc_id="y",
        title="Neurofibromatosis Type 1 — A Review",
        url="https://a.example/p2",
        internal=None,
    )
    kept, n = dedupe_documents([d1, d2])
    assert n == 1
    assert len(kept) == 1


def test_dedupe_does_not_merge_trials_with_different_nct():
    d1 = _doc(
        doc_id="t1",
        title="Trial for NF1",
        url="https://clinicaltrials.gov/study/NCT01234567",
        source="ClinicalTrials.gov",
        entity="clinical_trial",
        internal="i1",
        raw={"external_id": "NCT01234567"},
    )
    d2 = _doc(
        doc_id="t2",
        title="Trial for NF1",
        url="https://clinicaltrials.gov/study/NCT07654321",
        source="ClinicalTrials.gov",
        entity="clinical_trial",
        internal="i2",
        raw={"external_id": "NCT07654321"},
    )
    kept, n = dedupe_documents([d1, d2])
    assert n == 0
    assert len(kept) == 2


def test_trust_based_ranking_pubmed_vs_unknown():
    pub = _doc(
        doc_id="p",
        title="Completely different diabetes paper title alpha",
        url="https://pubmed/1",
        source="PubMed",
        rel=0.5,
    )
    low = _doc(
        doc_id="u",
        title="Unrelated rare disease blog post beta gamma",
        url="https://unknown.example/x",
        source="Random Blog",
        rel=0.5,
    )
    r = aggregate_and_rank([pub], [low], user_query="diabetes management", intent=UserIntent.latest_research)
    # PubMed is higher trust; titles differ so no dedupe removal.
    assert r.documents[0].source_name == "PubMed"


def test_merge_legacy_and_live_counts():
    legacy = _doc(
        doc_id="research_item:legacy-1",
        title="Old but trusted trial",
        url="https://clinicaltrials.gov/NCT00000001",
        source="ClinicalTrials.gov",
        entity="clinical_trial",
        rel=0.9,
    )
    live = NormalizedMedicalDocument(
        id="medlineplus:x",
        entity_type="disease",
        title="NF1 overview consumer",
        source_name="MedlinePlus (NLM)",
        source_url="https://medlineplus.gov/nf1.html",
        summary="Consumer summary",
        plain_language_summary="Simple NF1 text",
        condition_name="NF1",
        reliability_score=0.95,
        relevance_score=0.6,
        freshness_score=0.95,
        published_at=None,
        raw_data={"_provider": "medlineplus_nlm"},
        internal_research_item_id=None,
    )
    r = aggregate_and_rank([legacy], [live], user_query="what is NF1", intent=UserIntent.disease_overview)
    assert len(r.documents) == 2
    assert r.legacy_count == 1
    assert r.live_count == 1
    assert len(r.top_source_names) >= 1


def test_format_aggregated_includes_research_item_id_when_present():
    d = _doc(doc_id="research_item:rid-1", title="T", url="https://x", internal="rid-1")
    text = format_aggregated_evidence_for_prompt([d])
    assert "research_item_id=rid-1" in text


def test_title_similarity_high_for_near_dup():
    assert title_similarity("Type 1 Diabetes Mellitus", "Type 1 diabetes mellitus — guide") > 0.85


def test_composite_rank_respects_intent():
    trial = _doc(
        doc_id="t",
        title="Phase 2 trial recruiting",
        url="https://ct.gov/NCT09999999",
        source="ClinicalTrials.gov",
        entity="clinical_trial",
        rel=0.55,
    )
    paper = _doc(
        doc_id="p",
        title="Lab mouse study",
        url="https://pubmed/9",
        source="PubMed",
        entity="research_paper",
        rel=0.55,
    )
    st = composite_rank_score(trial, user_query="clinical trials recruiting", intent=UserIntent.clinical_trials)
    sp = composite_rank_score(paper, user_query="clinical trials recruiting", intent=UserIntent.clinical_trials)
    assert st > sp


def test_legacy_only_when_live_empty():
    """If live providers return nothing (e.g. all failed), aggregation still returns legacy."""
    legacy = [_doc(doc_id="l1", title="Safe legacy", url="https://pubmed/1")]
    r = aggregate_and_rank(legacy, [], user_query="q", intent=UserIntent.unknown)
    assert len(r.documents) == 1
    assert r.live_count == 0
    assert r.duplicates_removed == 0
