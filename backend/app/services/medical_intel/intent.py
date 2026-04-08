"""User intent for smart retrieval (heuristic, no extra API cost).

Future: optional LLM refinement behind a feature flag; keep heuristics as fallback.
"""

from __future__ import annotations

import re
from enum import Enum


class UserIntent(str, Enum):
    disease_overview = "disease_overview"
    symptoms = "symptoms"
    treatment = "treatment"
    latest_research = "latest_research"
    clinical_trials = "clinical_trials"
    drug_info = "drug_info"
    side_effects = "side_effects"
    prognosis = "prognosis"
    genetics = "genetics"
    urgent_warning = "urgent_warning"
    daily_life_help = "daily_life_help"
    unknown = "unknown"


def _lower(s: str) -> str:
    return s.strip().lower()


def infer_intent_heuristic(user_query: str) -> UserIntent:
    """Lightweight keyword router (English + common Hebrew fragments). Safe default: unknown."""
    q = _lower(user_query)
    if not q:
        return UserIntent.unknown

    # Urgent / red-flag (conservative; pairs checked in safety layer too)
    if re.search(r"\b(emergency|911|er\b|ambulance|suicide|chest pain)\b", q):
        return UserIntent.urgent_warning
    if any(x in q for x in ("מצב חירום", "כאב חזה", "אובדנות")):
        return UserIntent.urgent_warning

    if any(
        x in q
        for x in (
            "clinical trial",
            "nct",
            "recruiting",
            "ניסוי קליני",
            "גיוס",
        )
    ):
        return UserIntent.clinical_trials

    if any(x in q for x in ("latest research", "new study", "recent paper", "pubmed", "מחקר חדש", "מאמר")):
        return UserIntent.latest_research

    if any(x in q for x in ("side effect", "adverse", "תופעות לוואי", "תופעת לוואי")):
        return UserIntent.side_effects

    if any(x in q for x in ("drug", "medication", "תרופה", "תרופות")):
        return UserIntent.drug_info

    if any(x in q for x in ("treatment", "therapy", "טיפול", "שיקום")):
        return UserIntent.treatment

    if any(x in q for x in ("symptom", "sign", "תסמין", "סימפטום")):
        return UserIntent.symptoms

    if any(x in q for x in ("prognosis", "life expectancy", "צפי", "פרוגנוזה")):
        return UserIntent.prognosis

    if any(x in q for x in ("gene", "genetic", "mutation", "גן ", "גנטי", "מוטציה")):
        return UserIntent.genetics

    if any(x in q for x in ("daily life", "school", "work", "חיים יומיומיים", "בית ספר")):
        return UserIntent.daily_life_help

    if any(x in q for x in ("what is", "overview", "explain", "מה זה", "מהי ", "מידע על")):
        return UserIntent.disease_overview

    return UserIntent.unknown
