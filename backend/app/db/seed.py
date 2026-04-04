from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Condition, Source


def seed_initial_data() -> None:
    db = SessionLocal()
    try:
        if not db.scalar(select(Condition).where(Condition.slug == "nf1")):
            db.add(
                Condition(
                    canonical_name="Neurofibromatosis Type 1",
                    slug="nf1",
                    description="NF1 is a genetic condition that can affect nerves, skin, and other systems.",
                    synonyms=["NF1", "Neurofibromatosis 1", "von Recklinghausen disease"],
                    rare_disease_flag=True,
                )
            )

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
    print("Seeded NF1 and trusted sources.")
