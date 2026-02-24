import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit import AuditLog, AuditOverride


async def log_prescription_check(
    db: AsyncSession,
    doctor_id: str,
    patient_id: str,
    request_id: uuid.UUID,
    overall_signal: str,
    drug_results: list[dict],
    processing_ms: int,
    facility_id: str = "default",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit = AuditLog(
        event_type="PRESCRIPTION_CHECK",
        doctor_id=doctor_id,
        patient_id=patient_id,
        request_id=request_id,
        overall_signal=overall_signal,
        drug_results=drug_results,
        processing_ms=processing_ms,
        facility_id=facility_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    await db.flush()
    return audit


async def log_override(
    db: AsyncSession,
    doctor_id: str,
    patient_id: str,
    request_id: str,
    overridden_warnings: list[str],
    justification: str,
    digital_signature: str,
    facility_id: str = "default",
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit = AuditLog(
        event_type="OVERRIDE",
        doctor_id=doctor_id,
        patient_id=patient_id,
        request_id=uuid.UUID(request_id) if request_id else None,
        facility_id=facility_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit)
    await db.flush()

    override = AuditOverride(
        audit_id=audit.id,
        overridden_warnings=overridden_warnings,
        justification=justification,
        digital_signature=digital_signature,
    )
    db.add(override)
    await db.flush()
    return audit