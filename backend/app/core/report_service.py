import os
import uuid
import structlog
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.report import PatientReport
from app.models.patient import Patient
from app.core.ai_backends import get_ai_backend

logger = structlog.get_logger()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _ensure_upload_dir(patient_id: uuid.UUID) -> Path:
    """Create upload directory for patient if it doesn't exist."""
    patient_dir = UPLOAD_DIR / str(patient_id)
    patient_dir.mkdir(parents=True, exist_ok=True)
    return patient_dir


def _extract_text_from_pdf(file_path: str) -> str:
    """Extract text from a digital PDF using PyMuPDF."""
    import fitz  # PyMuPDF
    text_parts = []
    doc = fitz.open(file_path)
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts).strip()


def _pdf_pages_to_images(file_path: str) -> list[bytes]:
    """Convert each PDF page to a PNG image bytes for OCR via AI."""
    import fitz  # PyMuPDF
    images = []
    doc = fitz.open(file_path)
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        images.append(pix.tobytes("png"))
    doc.close()
    return images


async def _extract_text_from_image_via_ai(image_bytes: bytes) -> str:
    """Use MedGemma to extract text from a scanned report image."""
    import base64
    backend = get_ai_backend()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "You are a medical document reader. Extract ALL text content from this medical "
        "report/lab result image. Preserve the structure: test names, values, units, "
        "reference ranges, patient info, dates, doctor notes, diagnoses, medications. "
        "Return the extracted text as plain text, preserving the layout as much as possible."
    )

    try:
        if backend.supports_vision:
            content = await backend.chat_with_image(prompt, b64_image, temperature=0.1, max_tokens=2000)
            return content
        else:
            return ""
    except Exception as e:
        logger.error("report_image_extraction_failed", error=str(e))
        return ""


async def upload_and_extract(
    db: AsyncSession,
    patient: Patient,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> PatientReport:
    """Upload a report file, extract text, and store in DB."""
    patient_dir = _ensure_upload_dir(patient.id)
    file_id = uuid.uuid4()
    ext = os.path.splitext(filename)[1] or ".pdf"
    stored_filename = f"{file_id}{ext}"
    file_path = patient_dir / stored_filename

    # Write file to disk
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    # Create DB record
    report = PatientReport(
        id=file_id,
        patient_id=patient.id,
        filename=filename,
        file_path=str(file_path),
        file_size=len(file_bytes),
        content_type=content_type,
        status="extracting",
    )
    db.add(report)
    await db.flush()

    # Extract text
    extracted_text = ""
    try:
        if content_type == "application/pdf":
            extracted_text = _extract_text_from_pdf(str(file_path))
            # If PDF has very little text, it's likely scanned — convert pages to images and OCR
            if len(extracted_text.strip()) < 50:
                logger.info("pdf_appears_scanned", report_id=str(file_id))
                page_images = _pdf_pages_to_images(str(file_path))
                page_texts = []
                for img_bytes in page_images:
                    page_text = await _extract_text_from_image_via_ai(img_bytes)
                    if page_text:
                        page_texts.append(page_text)
                extracted_text = "\n\n".join(page_texts)
        elif content_type in ("image/jpeg", "image/png", "image/webp"):
            extracted_text = await _extract_text_from_image_via_ai(file_bytes)

        report.extracted_text = extracted_text
        report.status = "ready" if extracted_text else "failed"
        report.extracted_at = datetime.now(timezone.utc)

    except Exception as e:
        logger.error("text_extraction_failed", report_id=str(file_id), error=str(e))
        report.status = "failed"

    await db.commit()
    await db.refresh(report)
    return report


async def get_patient_reports(db: AsyncSession, patient_id: uuid.UUID) -> list[PatientReport]:
    """Get all reports for a patient."""
    result = await db.execute(
        select(PatientReport)
        .where(PatientReport.patient_id == patient_id)
        .order_by(PatientReport.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def get_report_by_id(db: AsyncSession, report_id: uuid.UUID) -> PatientReport | None:
    """Get a single report by ID."""
    result = await db.execute(
        select(PatientReport).where(PatientReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def delete_report(db: AsyncSession, report: PatientReport) -> None:
    """Delete a report and its file."""
    try:
        if os.path.exists(report.file_path):
            os.remove(report.file_path)
    except Exception as e:
        logger.warning("report_file_delete_failed", error=str(e))

    await db.delete(report)
    await db.commit()


async def get_all_report_texts(db: AsyncSession, patient_id: uuid.UUID) -> str:
    """Get concatenated extracted text from all ready reports for a patient."""
    result = await db.execute(
        select(PatientReport.extracted_text)
        .where(PatientReport.patient_id == patient_id)
        .where(PatientReport.status == "ready")
        .where(PatientReport.extracted_text.isnot(None))
        .order_by(PatientReport.uploaded_at.desc())
    )
    texts = [row[0] for row in result.all() if row[0]]
    return "\n\n---\n\n".join(texts)