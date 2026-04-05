from datetime import datetime

from pydantic import BaseModel, Field


class PrivateDocumentEnrichmentOut(BaseModel):
    patient_summary: str = Field(default="", max_length=12000)
    doctor_questions: list[str] = Field(default_factory=list, max_length=20)


class PrivateDocumentListItem(BaseModel):
    id: str
    original_filename: str
    processing_status: str
    patient_summary: str
    doctor_questions: list[str]
    created_at: datetime
