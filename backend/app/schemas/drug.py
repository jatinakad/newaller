from pydantic import BaseModel
from uuid import UUID


class IngredientOut(BaseModel):
    id: UUID
    name: str
    type: str
    strength: str | None = None
    chemical_family: str | None = None
    allergen_codes: list[str] | None = None

    model_config = {"from_attributes": True}


class DrugOut(BaseModel):
    id: UUID
    rxcui: str
    name: str
    generic_name: str | None = None
    dosage_form: str | None = None
    route: str | None = None
    brand_names: list[str] | None = None

    model_config = {"from_attributes": True}


class DrugWithIngredients(DrugOut):
    ingredients: list[IngredientOut] = []


class DrugSearchResult(BaseModel):
    results: list[DrugOut]
    total: int
