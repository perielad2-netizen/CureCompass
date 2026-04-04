def score_update(
    source_trust: float,
    recency_score: float,
    evidence_score: float,
    novelty_score: float,
    relevance_score: float,
    regulatory_significance: float,
    recruiting_boost: float,
    material_change_score: float,
) -> float:
    return (
        source_trust * 0.2
        + recency_score * 0.15
        + evidence_score * 0.2
        + novelty_score * 0.1
        + relevance_score * 0.15
        + regulatory_significance * 0.1
        + recruiting_boost * 0.05
        + material_change_score * 0.05
    )
