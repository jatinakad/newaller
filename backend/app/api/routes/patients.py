from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core import patient_service
from app.schemas.patient import (
    PatientOut,
    PatientAllergyProfile,
    PatientCreate,
    AllergyCreate,
    LabSensitivityCreate,
    ConditionCreate,
    AllergyOut,
    LabSensitivityOut,
    ConditionOut,
)

router = APIRouter(prefix="/api/v1/patients", tags=["patients"])


@router.post("", response_model=PatientOut, status_code=201)
async def create_patient(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
):
    existing = await patient_service.get_patient_by_external_id(db, data.external_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Patient with external_id '{data.external_id}' already exists")
    patient = await patient_service.create_patient(db, data)
    return patient


@router.get("/{patient_id}/allergy-profile", response_model=PatientAllergyProfile)
async def get_allergy_profile(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
):
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")

    return PatientAllergyProfile(
        id=patient.id,
        external_id=patient.external_id,
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        weight_kg=patient.weight_kg,
        allergies=[AllergyOut.model_validate(a) for a in patient.allergies],
        lab_sensitivities=[LabSensitivityOut.model_validate(ls) for ls in patient.lab_sensitivities],
        conditions=[ConditionOut.model_validate(c) for c in patient.conditions],
    )


@router.post("/{patient_id}/allergies", response_model=AllergyOut, status_code=201)
async def add_allergy(
    patient_id: str,
    data: AllergyCreate,
    db: AsyncSession = Depends(get_db),
):
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
    allergy = await patient_service.add_allergy(db, patient.id, data)
    return allergy


@router.post("/{patient_id}/lab-sensitivities", response_model=LabSensitivityOut, status_code=201)
async def add_lab_sensitivity(
    patient_id: str,
    data: LabSensitivityCreate,
    db: AsyncSession = Depends(get_db),
):
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
    lab = await patient_service.add_lab_sensitivity(db, patient.id, data)
    return lab


@router.post("/{patient_id}/conditions", response_model=ConditionOut, status_code=201)
async def add_condition(
    patient_id: str,
    data: ConditionCreate,
    db: AsyncSession = Depends(get_db),
):
    patient = await patient_service.get_patient_by_external_id(db, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
    condition = await patient_service.add_condition(db, patient.id, data)
    return condition