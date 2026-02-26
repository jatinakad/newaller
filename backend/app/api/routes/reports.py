from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core import patient_service, report_service
from app.schemas.report import ReportOut, ReportListOut

router = APIRouter(prefix="/api/v1/patients", tags=["reports"])

ALLOWED_TYPES = {
    "application/pdf",
    "image/jpeg",
    "image/png",
    "image/webp",
}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB


@router.post("/{patient_id}/reports", response_model=ReportOut, status_code=201)
async def upload_report(
    patient_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a patient report (PDF or image). Text is extracted automatically."""
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"File type '{file.content_type}' not supported. Use PDF, JPEG, PNG, or WebP.",
        )

    file_bytes = await file.read()
    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=422, detail="File must be under 20MB")

    report = await report_service.upload_and_extract(
        db=db,
        patient=patient,
        filename=file.filename or "report",
        file_bytes=file_bytes,
        content_type=file.content_type,
    )
    return report


@router.get("/{patient_id}/reports", response_model=ReportListOut)
async def list_reports(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    """List all uploaded reports for a patient."""
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    reports = await report_service.get_patient_reports(db, patient.id)
    return ReportListOut(
        reports=[ReportOut.model_validate(r) for r in reports],
        total=len(reports),
    )


@router.delete("/{patient_id}/reports/{report_id}", status_code=204)
async def delete_report(
    patient_id: str,
    report_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a patient report."""
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    import uuid as _uuid
    try:
        rid = _uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid report ID")

    report = await report_service.get_report_by_id(db, rid)
    if not report or report.patient_id != patient.id:
        raise HTTPException(status_code=404, detail="Report not found")

    await report_service.delete_report(db, report)