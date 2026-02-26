import time
import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core import patient_service, allergy_engine, audit_service, ai_service
from app.schemas.prescription import (
    PrescriptionCheckRequest,
    PrescriptionCheckResponse,
    DrugCheckResult,
    OverrideRequest,
    OverrideResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/api/v1/prescription", tags=["prescription"])


@router.post("/check", response_model=PrescriptionCheckResponse)
async def check_prescription_manual(
    body: PrescriptionCheckRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Check prescription drugs against patient allergy profile (manual entry).
    Uses MedGemma LLM for comprehensive ingredient + cross-reactivity analysis."""
    start = time.monotonic()
    request_id = uuid.uuid4()

    # Collect medicine names from input
    medicine_names = [d.name for d in body.drugs if d.name]
    if not medicine_names:
        raise HTTPException(status_code=422, detail="At least one drug name is required")

    # Run LLM-first allergy check
    result = await allergy_engine.check_prescription(db, body.patient_id, medicine_names)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Patient '{body.patient_id}' not found")

    processing_ms = int((time.monotonic() - start) * 1000)

    # Audit log
    try:
        await audit_service.log_prescription_check(
            db=db,
            doctor_id=request.headers.get("X-Doctor-Id", "anonymous"),
            patient_id=body.patient_id,
            request_id=request_id,
            overall_signal=result["overall_signal"],
            drug_results=[r.model_dump() for r in result["drug_results"]],
            processing_ms=processing_ms,
            facility_id=body.facility_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
    except Exception as e:
        logger.error("audit_log_failed", error=str(e))

    return PrescriptionCheckResponse(
        request_id=str(request_id),
        patient_id=body.patient_id,
        overall_signal=result["overall_signal"],
        drug_results=result["drug_results"],
        processing_time_ms=processing_ms,
        citations=result.get("citations", []),
    )


@router.post("/check/photo", response_model=PrescriptionCheckResponse)
async def check_prescription_photo(
    request: Request,
    patient_id: str = Form(...),
    facility_id: str = Form("default"),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Check prescription via photo upload — uses MedGemma for OCR + allergy analysis."""
    start = time.monotonic()
    request_id = uuid.uuid4()

    # 1. Validate image
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=422, detail="Image must be JPEG, PNG, or WebP")

    image_bytes = await image.read()
    if len(image_bytes) > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=422, detail="Image must be under 10MB")

    # 2. Verify patient exists
    profile = await patient_service.get_allergy_profile(db, patient_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    # 3. OCR via MedGemma — extract drug names from photo
    ocr_result = await ai_service.extract_drugs_from_image(image_bytes)
    extracted_drugs = ocr_result.get("drugs", [])
    confidence = ocr_result.get("confidence", 0.0)

    if not extracted_drugs or confidence < 0.3:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "OCR_EXTRACTION_FAILED",
                "message": "Could not extract drug names from image. Please retry with a clearer photo or enter drug names manually.",
                "ocr_confidence": confidence,
            },
        )

    # 4. Extract medicine names and run LLM-first allergy check
    extracted_names = [d.get("name", "") for d in extracted_drugs if d.get("name")]

    result = await allergy_engine.check_prescription(db, patient_id, extracted_names)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    processing_ms = int((time.monotonic() - start) * 1000)

    # 5. Audit log
    try:
        await audit_service.log_prescription_check(
            db=db,
            doctor_id=request.headers.get("X-Doctor-Id", "anonymous"),
            patient_id=patient_id,
            request_id=request_id,
            overall_signal=result["overall_signal"],
            drug_results=[r.model_dump() for r in result["drug_results"]],
            processing_ms=processing_ms,
            facility_id=facility_id,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
    except Exception as e:
        logger.error("audit_log_failed", error=str(e))

    return PrescriptionCheckResponse(
        request_id=str(request_id),
        patient_id=patient_id,
        overall_signal=result["overall_signal"],
        drug_results=result["drug_results"],
        processing_time_ms=processing_ms,
        ocr_confidence=confidence,
        extracted_drugs=extracted_names,
        citations=result.get("citations", []),
    )


@router.post("/override", response_model=OverrideResponse)
async def override_prescription(
    body: OverrideRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Doctor overrides a RED warning with clinical justification."""
    try:
        audit = await audit_service.log_override(
            db=db,
            doctor_id=request.headers.get("X-Doctor-Id", "anonymous"),
            patient_id=request.headers.get("X-Patient-Id", "unknown"),
            request_id=body.request_id,
            overridden_warnings=body.overridden_warnings,
            justification=body.clinical_justification,
            digital_signature=body.digital_signature,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("User-Agent"),
        )
        return OverrideResponse(
            audit_id=str(audit.id),
            status="OVERRIDE_RECORDED",
            message="Override recorded. This action has been logged for audit purposes.",
        )
    except Exception as e:
        logger.error("override_failed", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to record override")