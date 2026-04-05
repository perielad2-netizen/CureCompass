import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import settings
from app.db.session import SessionLocal, get_db
from app.models.entities import Condition, User, UserFollowedCondition, UserPrivateDocument
from app.schemas.private_document import PrivateDocumentListItem
from app.services.private_document_pipeline import document_abs_path, process_uploaded_document

router = APIRouter(tags=["documents"])

ALLOWED_PDF = "application/pdf"
_MAX_UPLOAD = settings.private_document_max_bytes


def _require_follow(db: Session, user_id: uuid.UUID, condition: Condition) -> None:
    follow = db.scalar(
        select(UserFollowedCondition).where(
            UserFollowedCondition.user_id == user_id,
            UserFollowedCondition.condition_id == condition.id,
        )
    )
    if not follow:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Follow this condition to manage documents.")


def _process_doc_background(doc_id: uuid.UUID, answer_locale: str) -> None:
    db = SessionLocal()
    try:
        process_uploaded_document(db, doc_id, answer_locale=answer_locale)
    finally:
        db.close()


def _list_item(d: UserPrivateDocument) -> PrivateDocumentListItem:
    qs = d.doctor_questions_json if isinstance(d.doctor_questions_json, list) else []
    return PrivateDocumentListItem(
        id=str(d.id),
        original_filename=d.original_filename,
        processing_status=d.processing_status,
        patient_summary=d.patient_summary or "",
        doctor_questions=[str(x) for x in qs][:20],
        created_at=d.created_at,
    )


@router.get("/conditions/{slug}/documents", response_model=list[PrivateDocumentListItem])
def list_documents(
    slug: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    _require_follow(db, current_user.id, condition)

    rows = db.scalars(
        select(UserPrivateDocument)
        .where(UserPrivateDocument.user_id == current_user.id, UserPrivateDocument.condition_id == condition.id)
        .order_by(UserPrivateDocument.created_at.desc())
    ).all()
    return [_list_item(r) for r in rows]


@router.post("/conditions/{slug}/documents", response_model=PrivateDocumentListItem, status_code=status.HTTP_201_CREATED)
def upload_document(
    slug: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    file: UploadFile = File(...),
    consent_accepted: str = Form(...),
    answer_locale: str = Form("en"),
):
    if consent_accepted.lower() not in ("true", "1", "yes", "on"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must confirm consent before uploading (consent_accepted).",
        )
    locale = answer_locale if answer_locale in ("en", "he") else "en"

    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    _require_follow(db, current_user.id, condition)

    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing filename.")
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct != ALLOWED_PDF:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF uploads are supported in this version.")

    raw = file.file.read(_MAX_UPLOAD + 1)
    if len(raw) > _MAX_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_UPLOAD // (1024 * 1024)} MiB).",
        )
    if not raw.startswith(b"%PDF"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File does not look like a valid PDF.")

    doc_id = uuid.uuid4()
    stored = f"{doc_id}.pdf"
    user_dir = Path(settings.private_documents_dir).resolve() / str(current_user.id)
    user_dir.mkdir(parents=True, exist_ok=True)
    dest = user_dir / stored
    dest.write_bytes(raw)

    doc = UserPrivateDocument(
        id=doc_id,
        user_id=current_user.id,
        condition_id=condition.id,
        original_filename=file.filename[:500],
        stored_filename=stored,
        mime_type=ALLOWED_PDF,
        size_bytes=len(raw),
        processing_status="pending",
        consent_recorded_at=datetime.now(timezone.utc),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background_tasks.add_task(_process_doc_background, doc.id, locale)
    return _list_item(doc)


@router.delete("/conditions/{slug}/documents/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_document(
    slug: str,
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    condition = db.scalar(select(Condition).where(Condition.slug == slug))
    if not condition:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Condition not found")
    _require_follow(db, current_user.id, condition)

    try:
        did = uuid.UUID(document_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid document id") from exc

    doc = db.scalar(
        select(UserPrivateDocument).where(
            UserPrivateDocument.id == did,
            UserPrivateDocument.user_id == current_user.id,
            UserPrivateDocument.condition_id == condition.id,
        )
    )
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    path = document_abs_path(doc)
    db.delete(doc)
    db.commit()
    try:
        if path.is_file():
            path.unlink()
    except OSError:
        pass
    return Response(status_code=status.HTTP_204_NO_CONTENT)
