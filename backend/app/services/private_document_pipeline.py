"""PDF text extraction and plain-language enrichment for user uploads."""

from __future__ import annotations

import json
import logging
import re
import uuid
from pathlib import Path

from openai import OpenAI
from pypdf import PdfReader
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.entities import UserPrivateDocument
from app.schemas.private_document import PrivateDocumentEnrichmentOut
from app.services.openai_json_schema import patch_json_schema_for_openai_strict

logger = logging.getLogger(__name__)

_MAX_CONTEXT_PER_DOC = 12_000


def extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF page extract failed: %s", exc)
            t = ""
        parts.append(t)
    raw = "\n".join(parts)
    raw = re.sub(r"\s+", " ", raw).strip()
    cap = settings.private_document_max_extracted_chars
    if len(raw) > cap:
        raw = raw[:cap] + "\n\n[Text truncated for storage.]"
    return raw


def _enrichment_schema_config() -> dict:
    schema = PrivateDocumentEnrichmentOut.model_json_schema()
    patch_json_schema_for_openai_strict(schema)
    return {
        "format": {
            "type": "json_schema",
            "name": "PrivateDocumentEnrichmentOut",
            "schema": schema,
            "strict": True,
        }
    }


def enrich_document_text(*, text: str, condition_name: str, answer_locale: str) -> PrivateDocumentEnrichmentOut:
    lang = "Hebrew" if answer_locale == "he" else "English"
    system = (
        "You help patients understand their own medical documents. "
        "Output JSON only. Do not diagnose or recommend treatments or doses. "
        f"Write patient_summary and doctor_questions in {lang} (plain language). "
        "doctor_questions should be short questions for the patient's clinician about the document, not commands."
    )
    user = (
        f"Condition context (organizing topic only): {condition_name}\n\n"
        "Extracted document text:\n"
        f"{text[:50_000]}\n"
    )
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.responses.create(
        model=settings.openai_responses_model,
        input=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        text=_enrichment_schema_config(),
        timeout=120,
    )
    raw = getattr(response, "output_text", None)
    if not raw:
        raw = response.output[0].content[0].text  # type: ignore[index, union-attr]
    return PrivateDocumentEnrichmentOut.model_validate(json.loads(raw))


def document_abs_path(doc: UserPrivateDocument) -> Path:
    base = Path(settings.private_documents_dir).resolve()
    return (base / str(doc.user_id) / doc.stored_filename).resolve()


def process_uploaded_document(db: Session, doc_id: uuid.UUID, *, answer_locale: str) -> None:
    doc = db.get(UserPrivateDocument, doc_id)
    if not doc:
        return
    path = document_abs_path(doc)
    if not path.is_file():
        doc.processing_status = "failed"
        doc.processing_error = "Stored file missing."
        db.commit()
        return
    try:
        text = extract_pdf_text(path)
    except Exception as exc:  # noqa: BLE001
        logger.exception("PDF extraction failed for %s", doc_id)
        doc.processing_status = "failed"
        doc.processing_error = str(exc)[:2000]
        db.commit()
        return

    if not text or len(text.strip()) < 20:
        doc.processing_status = "failed"
        doc.processing_error = "No readable text found (scanned PDFs need OCR; not supported in this version)."
        doc.extracted_text = text or ""
        db.commit()
        return

    doc.extracted_text = text
    db.flush()

    try:
        from app.models.entities import Condition

        condition = db.get(Condition, doc.condition_id)
        cname = condition.canonical_name if condition else "Unknown condition"
        enriched = enrich_document_text(text=text, condition_name=cname, answer_locale=answer_locale)
        doc.patient_summary = enriched.patient_summary[:12000]
        doc.doctor_questions_json = enriched.doctor_questions[:20]
        doc.processing_status = "ready"
        doc.processing_error = ""
    except Exception as exc:  # noqa: BLE001
        logger.exception("Document enrichment failed for %s", doc_id)
        doc.processing_status = "failed"
        doc.processing_error = f"Summary step failed: {exc}"[:2000]
    db.commit()


def build_private_context_chunks(docs: list[UserPrivateDocument]) -> tuple[str, dict[str, UserPrivateDocument]]:
    """Returns context block and map document_id -> row for citation validation."""
    allowed: dict[str, UserPrivateDocument] = {}
    chunks: list[str] = []
    for d in docs:
        if d.processing_status != "ready" or not d.extracted_text:
            continue
        body = d.extracted_text[:_MAX_CONTEXT_PER_DOC]
        sid = str(d.id)
        allowed[sid] = d
        summary_bit = (d.patient_summary or "")[:2000]
        chunks.append(
            "\n".join(
                [
                    f"DOCUMENT_ID: {sid}",
                    f"Filename: {d.original_filename}",
                    f"Precomputed patient-facing summary (may omit details): {summary_bit}",
                    f"Extracted text:\n{body}",
                ]
            )
        )
    return "\n\n---\n\n".join(chunks), allowed
