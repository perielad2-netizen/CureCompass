"""Admin Source.enabled gates live MedicalIntel providers."""

from __future__ import annotations

from unittest.mock import MagicMock

from app.services.medical_intel.intent import UserIntent
from app.services.medical_intel.registry import (
    filter_live_providers_by_source_enabled,
    providers_for_intent,
)


def test_filter_removes_disabled_mapped_sources():
    provs = providers_for_intent(UserIntent.disease_overview)
    assert {p.provider_id for p in provs} >= {"orphadata", "medlineplus_nlm"}

    mock_db = MagicMock()
    mock_db.execute.return_value.all.return_value = [
        ("Orphanet (Orphadata)", False),
        ("MedlinePlus (NLM)", True),
    ]
    filtered = filter_live_providers_by_source_enabled(mock_db, provs)
    assert [p.provider_id for p in filtered] == ["medlineplus_nlm"]


def test_filter_keeps_all_when_db_has_no_matching_rows():
    provs = providers_for_intent(UserIntent.disease_overview)
    mock_db = MagicMock()
    mock_db.execute.return_value.all.return_value = []
    filtered = filter_live_providers_by_source_enabled(mock_db, provs)
    assert len(filtered) == len(provs)


def test_filter_empty_providers():
    mock_db = MagicMock()
    assert filter_live_providers_by_source_enabled(mock_db, []) == []
