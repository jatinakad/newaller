import json
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.patient import Patient, PatientAllergy, LabSensitivity, PatientCondition
from app.schemas.patient import PatientCreate, AllergyCreate, LabSensitivityCreate, ConditionCreate
from app.db.redis import redis_client

CACHE_TTL_PROFILE = 900  # 15 minutes


async def get_patient_by_external_id(db: AsyncSession, external_id: str) -> Patient | None:
    stmt = (
        select(Patient)
        .options(
            selectinload(Patient.allergies),
            selectinload(Patient.lab_sensitivities),
            selectinload(Patient.conditions),
        )
        .where(Patient.external_id == external_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_allergy_profile(db: AsyncSession, patient_external_id: str) -> dict | None:
    cache_key = f"patient_profile:{patient_external_id}"
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    patient = await get_patient_by_external_id(db, patient_external_id)
    if not patient:
        return None

    profile = {
        "patient_id": str(patient.id),
        "external_id": patient.external_id,
        "name": patient.name,
        "age": patient.age,
        "gender": patient.gender,
        "known_allergens": [
            {
                "allergen_name": a.allergen_name,
                "allergen_code": a.allergen_code,
                "category": a.category,
                "criticality": a.criticality,
                "reaction_manifestations": a.reaction_manifestations or [],
                "reaction_severity": a.reaction_severity,
                "verification_status": a.verification_status,
            }
            for a in patient.allergies
        ],
        "lab_sensitivities": [
            {
                "test_name": ls.test_name,
                "test_code": ls.test_code,
                "value": ls.value,
                "unit": ls.unit,
                "reference_range": ls.reference_range,
                "interpretation": ls.interpretation,
                "related_substances": ls.related_substances or [],
            }
            for ls in patient.lab_sensitivities
        ],
        "conditions": [
            {
                "condition_name": c.condition_name,
                "condition_code": c.condition_code,
                "contraindicated_ingredients": c.contraindicated_ingredients or [],
            }
            for c in patient.conditions
        ],
    }

    await redis_client.setex(cache_key, CACHE_TTL_PROFILE, json.dumps(profile))
    return profile


async def create_patient(db: AsyncSession, data: PatientCreate) -> Patient:
    patient = Patient(
        external_id=data.external_id,
        name=data.name,
        age=data.age,
        gender=data.gender,
        weight_kg=data.weight_kg,
    )
    db.add(patient)
    await db.flush()
    return patient


async def add_allergy(db: AsyncSession, patient_id, data: AllergyCreate) -> PatientAllergy:
    allergy = PatientAllergy(
        patient_id=patient_id,
        allergen_code=data.allergen_code,
        allergen_name=data.allergen_name,
        category=data.category,
        criticality=data.criticality,
        reaction_manifestations=data.reaction_manifestations,
        reaction_severity=data.reaction_severity,
        verification_status=data.verification_status,
    )
    db.add(allergy)
    await db.flush()
    return allergy


async def add_lab_sensitivity(db: AsyncSession, patient_id, data: LabSensitivityCreate) -> LabSensitivity:
    lab = LabSensitivity(
        patient_id=patient_id,
        test_code=data.test_code,
        test_name=data.test_name,
        value=data.value,
        unit=data.unit,
        reference_range=data.reference_range,
        interpretation=data.interpretation,
        related_substances=data.related_substances,
    )
    db.add(lab)
    await db.flush()
    return lab


async def add_condition(db: AsyncSession, patient_id, data: ConditionCreate) -> PatientCondition:
    condition = PatientCondition(
        patient_id=patient_id,
        condition_code=data.condition_code,
        condition_name=data.condition_name,
        contraindicated_ingredients=data.contraindicated_ingredients,
    )
    db.add(condition)
    await db.flush()
    return condition


