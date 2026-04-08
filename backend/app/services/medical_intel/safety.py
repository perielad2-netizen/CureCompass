"""Conservative non-clinical guardrails (hints only; never a diagnosis)."""

from __future__ import annotations

import re


def medical_attention_hints(user_query: str, *, locale: str = "en") -> list[str]:
    """Return short reminders to seek professional care when red-flag phrases appear.

    Complements Ask AI system prompts; does not replace them. Empty list when no match.
    """
    q = user_query.strip().lower()
    hints: list[str] = []

    # English patterns (very narrow to avoid alarm fatigue)
    if re.search(r"\b(severe|sudden)\s+(headache|pain)\b", q) or re.search(
        r"\b(vomiting|vomit).{0,40}(neurolog|seizure|stroke)\b", q
    ):
        hints.append(
            "If you or someone else has severe or sudden symptoms, contact a clinician or emergency services right away."
        )

    if "חולשה" in user_query or "הקאות" in user_query:
        if any(x in user_query for x in ("עווית", "נוירולוג", "שבץ", "פרכוס")):
            hints.append("במקרה של תסמינים חמורים או חריגים פנו מיד לרופא או לשירותי חירום.")

    if locale == "he" and not hints and any(
        x in user_query.lower() for x in ("כאב חזק", "קושי לנשום", "אובדן הכרה")
    ):
        hints.append("תסמינים חמורים דורשים פנייה לרפואה דחופה.")

    return hints
