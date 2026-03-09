import os
import uuid
import tempfile
import structlog
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.report import PatientReport
from app.models.patient import Patient
from app.core.ai_backends import get_ai_backend
from app.config import get_settings

logger = structlog.get_logger()

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"


def _get_s3_client():
    """Get boto3 S3 client. Uses IAM role if no explicit keys."""
    import boto3
    settings = get_settings()
    kwargs = {"region_name": settings.S3_REGION}
    if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
        kwargs["aws_access_key_id"] = settings.AWS_ACCESS_KEY_ID
        kwargs["aws_secret_access_key"] = settings.AWS_SECRET_ACCESS_KEY
    return boto3.client("s3", **kwargs)


def _upload_to_s3(file_bytes: bytes, s3_key: str, content_type: str) -> str:
    """Upload file bytes to S3 and return the S3 key."""
    settings = get_settings()
    s3 = _get_s3_client()
    s3.put_object(
        Bucket=settings.S3_BUCKET,
        Key=s3_key,
        Body=file_bytes,
        ContentType=content_type,
    )
    logger.info("s3_upload_success", bucket=settings.S3_BUCKET, key=s3_key)
    return s3_key


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


async def _parse_text_to_structured_data(raw_text: str) -> dict | None:
    """Use Gemini AI to parse raw extracted text into structured medical data JSON."""
    if not raw_text or len(raw_text.strip()) < 20:
        return None

    backend = get_ai_backend()
    prompt = (
        "You are a medical data extraction AI. Parse the following medical document text "
        "into a structured JSON object. Extract ALL relevant information into these categories:\n\n"
        "{\n"
        '  "document_type": "lab_report | prescription | discharge_summary | radiology | pathology | other",\n'
        '  "patient_info": { "name": "", "id": "", "age": "", "gender": "", "date_of_birth": "" },\n'
        '  "document_date": "YYYY-MM-DD or raw date string",\n'
        '  "doctor_info": { "name": "", "specialty": "", "facility": "" },\n'
        '  "medications": [\n'
        '    { "name": "", "dosage": "", "frequency": "", "route": "", "duration": "", "instructions": "" }\n'
        "  ],\n"
        '  "lab_results": [\n'
        '    { "test_name": "", "value": "", "unit": "", "reference_range": "", "interpretation": "normal|high|low|critical" }\n'
        "  ],\n"
        '  "diagnoses": [\n'
        '    { "condition": "", "icd_code": "", "status": "active|resolved|suspected" }\n'
        "  ],\n"
        '  "allergies_mentioned": ["substance1", "substance2"],\n'
        '  "vitals": [\n'
        '    { "name": "", "value": "", "unit": "" }\n'
        "  ],\n"
        '  "procedures": [\n'
        '    { "name": "", "date": "", "notes": "" }\n'
        "  ],\n"
        '  "clinical_notes": "any free-text clinical observations or notes",\n'
        '  "summary": "A brief 2-3 sentence summary of the document"\n'
        "}\n\n"
        "Rules:\n"
        "- Only include categories that have actual data. Omit empty arrays/objects.\n"
        "- For lab results, always try to determine interpretation (normal/high/low/critical).\n"
        "- Return ONLY valid JSON, no markdown fences, no explanation.\n"
        "- If the text is not a medical document, return {\"document_type\": \"other\", \"summary\": \"...\"}\n\n"
        f"Document text:\n{raw_text[:8000]}"
    )

    try:
        messages = [{"role": "user", "content": prompt}]
        response = await backend.chat(messages, temperature=0.1, max_tokens=3000)
        # Parse JSON from response
        import json
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[-1]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()
        return json.loads(cleaned)
    except Exception as e:
        logger.error("structured_data_parsing_failed", error=str(e))
        return None


async def upload_and_extract(
    db: AsyncSession,
    patient: Patient,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> PatientReport:
    """Upload a report file, extract text, and store in DB.
    Supports both local disk (dev) and S3 (production) storage."""
    settings = get_settings()
    file_id = uuid.uuid4()
    ext = os.path.splitext(filename)[1] or ".pdf"
    stored_filename = f"{file_id}{ext}"

    # Write to local disk (always needed for PDF text extraction)
    if settings.USE_S3:
        # Use temp dir for extraction, then upload to S3
        tmp_dir = Path(tempfile.mkdtemp())
        local_file_path = tmp_dir / stored_filename
    else:
        patient_dir = _ensure_upload_dir(patient.id)
        local_file_path = patient_dir / stored_filename

    with open(local_file_path, "wb") as f:
        f.write(file_bytes)

    # Determine storage path
    if settings.USE_S3:
        s3_key = f"reports/{patient.id}/{stored_filename}"
        _upload_to_s3(file_bytes, s3_key, content_type)
        stored_path = f"s3://{settings.S3_BUCKET}/{s3_key}"
    else:
        stored_path = str(local_file_path)

    # Create DB record
    report = PatientReport(
        id=file_id,
        patient_id=patient.id,
        filename=filename,
        file_path=stored_path,
        file_size=len(file_bytes),
        content_type=content_type,
        status="extracting",
    )
    db.add(report)
    await db.flush()

    # Extract text (uses local file)
    extracted_text = ""
    try:
        if content_type == "application/pdf":
            extracted_text = _extract_text_from_pdf(str(local_file_path))
            # If PDF has very little text, it's likely scanned — convert pages to images and OCR
            if len(extracted_text.strip()) < 50:
                logger.info("pdf_appears_scanned", report_id=str(file_id))
                page_images = _pdf_pages_to_images(str(local_file_path))
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

        # Parse extracted text into structured data using AI
        if extracted_text:
            try:
                structured = await _parse_text_to_structured_data(extracted_text)
                report.structured_data = structured
                logger.info("structured_data_parsed", report_id=str(file_id), has_data=structured is not None)
            except Exception as se:
                logger.error("structured_parsing_failed", report_id=str(file_id), error=str(se))

    except Exception as e:
        logger.error("text_extraction_failed", report_id=str(file_id), error=str(e))
        report.status = "failed"

    # Cleanup temp file if using S3
    if settings.USE_S3:
        try:
            os.remove(local_file_path)
            os.rmdir(local_file_path.parent)
        except OSError:
            pass

    await db.commit()
    await db.refresh(report)
    return report


async def get_patient_reports(db: AsyncSession, patient_id: uuid.UUID) -> list[PatientReport]:
    """Get all latest-version reports for a patient."""
    result = await db.execute(
        select(PatientReport)
        .where(PatientReport.patient_id == patient_id)
        .where(PatientReport.is_latest == True)
        .order_by(PatientReport.uploaded_at.desc())
    )
    return list(result.scalars().all())


async def get_report_by_id(db: AsyncSession, report_id: uuid.UUID) -> PatientReport | None:
    """Get a single report by ID."""
    result = await db.execute(
        select(PatientReport).where(PatientReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def replace_report(
    db: AsyncSession,
    old_report: PatientReport,
    patient: Patient,
    filename: str,
    file_bytes: bytes,
    content_type: str,
) -> PatientReport:
    """Upload a new version of a report. Old version is kept but marked superseded."""
    new_report = await upload_and_extract(
        db=db,
        patient=patient,
        filename=filename,
        file_bytes=file_bytes,
        content_type=content_type,
    )
    new_report.version = old_report.version + 1

    old_report.is_latest = False
    old_report.superseded_by = new_report.id

    await db.commit()
    await db.refresh(new_report)
    return new_report


async def get_all_report_texts(db: AsyncSession, patient_id: uuid.UUID) -> str:
    """Get concatenated extracted text from all latest ready reports for a patient.
    Prefers structured_data summaries when available, falls back to raw extracted_text."""
    import json
    result = await db.execute(
        select(PatientReport.extracted_text, PatientReport.structured_data)
        .where(PatientReport.patient_id == patient_id)
        .where(PatientReport.status == "ready")
        .where(PatientReport.is_latest == True)
        .where(PatientReport.extracted_text.isnot(None))
        .order_by(PatientReport.uploaded_at.desc())
    )
    parts = []
    for row in result.all():
        raw_text, structured = row[0], row[1]
        if structured:
            # Build a concise structured summary for AI context
            lines = []
            if structured.get("document_type"):
                lines.append(f"Document type: {structured['document_type']}")
            if structured.get("summary"):
                lines.append(f"Summary: {structured['summary']}")
            if structured.get("medications"):
                med_names = [m.get("name", "") + (" " + m.get("dosage", "")).strip() for m in structured["medications"]]
                lines.append(f"Medications: {', '.join(med_names)}")
            if structured.get("lab_results"):
                for lr in structured["lab_results"]:
                    lines.append(f"Lab: {lr.get('test_name', '')} = {lr.get('value', '')} {lr.get('unit', '')} ({lr.get('interpretation', 'unknown')})")
            if structured.get("diagnoses"):
                diag_names = [d.get("condition", "") for d in structured["diagnoses"]]
                lines.append(f"Diagnoses: {', '.join(diag_names)}")
            if structured.get("allergies_mentioned"):
                lines.append(f"Allergies mentioned in report: {', '.join(structured['allergies_mentioned'])}")
            if structured.get("vitals"):
                vital_strs = [f"{v.get('name','')}: {v.get('value','')} {v.get('unit','')}" for v in structured["vitals"]]
                lines.append(f"Vitals: {', '.join(vital_strs)}")
            if structured.get("clinical_notes"):
                lines.append(f"Clinical notes: {structured['clinical_notes']}")
            parts.append("\n".join(lines))
        elif raw_text:
            parts.append(raw_text)
    return "\n\n---\n\n".join(parts)


