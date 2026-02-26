from pydantic import BaseModel
from uuid import UUID


class DrugInput(BaseModel):
    rxcui: str | None = None
    name: str | None = None


class PrescriptionCheckRequest(BaseModel):
    patient_id: str
    drugs: list[DrugInput]
    facility_id: str = "default"


class Warning(BaseModel):
    warning_id: str
    severity: str  # CRITICAL, HIGH, MODERATE, LOW
    type: str  # DIRECT_ALLERGEN_MATCH, CROSS_REACTIVITY, LAB_SENSITIVITY, CONDITION_CONTRAINDICATION, EXCIPIENT_ALLERGY
    ingredient: str
    allergen: str
    message: str
    evidence: dict


class AlternativeDrug(BaseModel):
    rxcui: str
    name: str
    reason: str
    signal: str = "GREEN"


class DrugCheckResult(BaseModel):
    drug: dict  # {rxcui, name}
    signal: str  # GREEN, YELLOW, RED
    warnings: list[Warning] = []
    alternatives: list[AlternativeDrug] = []


class Citation(BaseModel):
    source: str
    url: str


class PrescriptionCheckResponse(BaseModel):
    request_id: str
    patient_id: str
    overall_signal: str
    drug_results: list[DrugCheckResult]
    processing_time_ms: int
    ocr_confidence: float | None = None
    extracted_drugs: list[str] | None = None
    citations: list[Citation] = []


class OverrideRequest(BaseModel):
    request_id: str
    overridden_warnings: list[str]
    clinical_justification: str
    digital_signature: str


class OverrideResponse(BaseModel):
    audit_id: str
    status: str
    message: str