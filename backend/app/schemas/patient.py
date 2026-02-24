from pydantic import BaseModel
from uuid import UUID
from datetime import datetime


class AllergyOut(BaseModel):
    id: UUID
    allergen_code: str | None = None
    allergen_name: str
    category: str
    criticality: str
    reaction_manifestations: list[str] | None = None
    reaction_severity: str | None = None
    verification_status: str
    recorded_date: datetime | None = None

    model_config = {"from_attributes": True}


class LabSensitivityOut(BaseModel):
    id: UUID
    test_code: str | None = None
    test_name: str
    value: float
    unit: str
    reference_range: str | None = None
    interpretation: str
    related_substances: list[str] | None = None
    report_date: datetime | None = None

    model_config = {"from_attributes": True}


class ConditionOut(BaseModel):
    id: UUID
    condition_code: str | None = None
    condition_name: str
    contraindicated_ingredients: list[str] | None = None

    model_config = {"from_attributes": True}


class PatientOut(BaseModel):
    id: UUID
    external_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    weight_kg: float | None = None

    model_config = {"from_attributes": True}


class PatientAllergyProfile(PatientOut):
    allergies: list[AllergyOut] = []
    lab_sensitivities: list[LabSensitivityOut] = []
    conditions: list[ConditionOut] = []


class PatientCreate(BaseModel):
    external_id: str
    name: str
    age: int | None = None
    gender: str | None = None
    weight_kg: float | None = None


class AllergyCreate(BaseModel):
    allergen_code: str | None = None
    allergen_name: str
    category: str = "drug"
    criticality: str = "high"
    reaction_manifestations: list[str] | None = None
    reaction_severity: str | None = None
    verification_status: str = "confirmed"


class LabSensitivityCreate(BaseModel):
    test_code: str | None = None
    test_name: str
    value: float
    unit: str
    reference_range: str | None = None
    interpretation: str = "normal"
    related_substances: list[str] | None = None


class ConditionCreate(BaseModel):
    condition_code: str | None = None
    condition_name: str
    contraindicated_ingredients: list[str] | None = None