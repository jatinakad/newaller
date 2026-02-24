from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core import drug_service
from app.schemas.drug import DrugOut, DrugSearchResult, DrugWithIngredients, IngredientOut

router = APIRouter(prefix="/api/v1/drugs", tags=["drugs"])


@router.get("/search", response_model=DrugSearchResult)
async def search_drugs(
    q: str = Query(..., min_length=2, description="Drug name search query"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    drugs = await drug_service.search_drugs(db, q, limit)
    return DrugSearchResult(
        results=[
            DrugOut(
                id=d.id,
                rxcui=d.rxcui,
                name=d.name,
                generic_name=d.generic_name,
                dosage_form=d.dosage_form,
                route=d.route,
                brand_names=d.brand_names,
            )
            for d in drugs
        ],
        total=len(drugs),
    )


@router.get("/{rxcui}/ingredients")
async def get_drug_ingredients(
    rxcui: str,
    db: AsyncSession = Depends(get_db),
):
    drug = await drug_service.get_drug_by_rxcui(db, rxcui)
    if not drug:
        raise HTTPException(status_code=404, detail=f"Drug with rxcui '{rxcui}' not found")

    ingredients = await drug_service.get_drug_ingredients(db, drug)
    return {
        "rxcui": drug.rxcui,
        "name": drug.name,
        "ingredients": ingredients,
    }