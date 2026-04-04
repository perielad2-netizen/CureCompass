from fastapi import HTTPException, status


DISALLOWED_PATTERNS = [
    "diagnose",
    "dosage",
    "dose",
    "emergency",
    "chest pain",
    "suicidal",
    "stroke",
    "heart attack",
    "911",
]


def enforce_condition_scope(prompt: str, condition_name: str) -> None:
    lowered = prompt.lower()
    # Since endpoint is condition-scoped, we mainly block clearly unrelated/general prompts.
    unrelated_patterns = [
        "weather",
        "movie",
        "sports",
        "programming",
        "javascript",
        "bitcoin",
        "travel plan",
    ]
    if any(term in lowered for term in unrelated_patterns):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Ask AI is limited to your selected condition.")
    if any(term in lowered for term in DISALLOWED_PATTERNS):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CureCompass explains research updates only. For personal medical advice, please consult a clinician.",
        )
