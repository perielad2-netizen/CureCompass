from sqlalchemy import select

from app.db.conditions_catalog import CONDITIONS
from app.db.session import SessionLocal
from app.models.entities import Condition, Source


def upsert_conditions(db) -> int:
    """Insert missing conditions or refresh catalog fields for existing slugs. Returns rows touched."""
    n = 0
    for row in CONDITIONS:
        slug = row["slug"]
        existing = db.scalar(select(Condition).where(Condition.slug == slug))
        if existing:
            existing.canonical_name = row["canonical_name"]
            existing.description = row["description"]
            existing.synonyms = row["synonyms"]
            existing.rare_disease_flag = row["rare_disease_flag"]
            n += 1
        else:
            db.add(
                Condition(
                    canonical_name=row["canonical_name"],
                    slug=slug,
                    description=row["description"],
                    synonyms=row["synonyms"],
                    rare_disease_flag=row["rare_disease_flag"],
                )
            )
            n += 1
    return n


def seed_initial_data() -> None:
    db = SessionLocal()
    try:
        upsert_conditions(db)

        for name, source_type, base_url, trust in [
            ("PubMed", "papers", "https://pubmed.ncbi.nlm.nih.gov", 0.96),
            ("ClinicalTrials.gov", "trials", "https://clinicaltrials.gov", 0.97),
            ("openFDA", "regulatory", "https://api.fda.gov", 0.95),
        ]:
            existing = db.scalar(select(Source).where(Source.name == name))
            if not existing:
                db.add(Source(name=name, source_type=source_type, base_url=base_url, trust_score=trust))
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_initial_data()
    print(f"Seeded/updated {len(CONDITIONS)} conditions and trusted sources.")
