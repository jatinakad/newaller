# Drug lookup and cross-reactivity helpers

def find_drug_by_name(name: str):
    return None
import json
import uuid
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.models.drug import Drug, Ingredient, DrugIngredient, CrossReactivityGroup, CrossReactivityMember
from app.db.redis import redis_client


CACHE_TTL_DRUG = 86400  # 24 hours
CACHE_TTL_SEARCH = 3600  # 1 hour


async def search_drugs(db: AsyncSession, query: str, limit: int = 10) -> list[Drug]:
    cache_key = f"drug_search:{query.lower()}:{limit}"
    cached = await redis_client.get(cache_key)
    if cached:
        drug_ids = json.loads(cached)
        if not drug_ids:
            return []
        stmt = select(Drug).where(Drug.id.in_([uuid.UUID(d) for d in drug_ids]))
        result = await db.execute(stmt)
        return list(result.scalars().all())

    stmt = (
        select(Drug)
        .where(
            func.similarity(Drug.name, query) > 0.1
        )
        .order_by(func.similarity(Drug.name, query).desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    drugs = list(result.scalars().all())

    await redis_client.setex(cache_key, CACHE_TTL_SEARCH, json.dumps([str(d.id) for d in drugs]))
    return drugs


async def get_drug_by_rxcui(db: AsyncSession, rxcui: str) -> Drug | None:
    cache_key = f"drug:rxcui:{rxcui}"
    cached = await redis_client.get(cache_key)
    if cached:
        drug_id = cached
        stmt = (
            select(Drug)
            .options(selectinload(Drug.ingredients).selectinload(DrugIngredient.ingredient))
            .where(Drug.id == uuid.UUID(drug_id))
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    stmt = (
        select(Drug)
        .options(selectinload(Drug.ingredients).selectinload(DrugIngredient.ingredient))
        .where(Drug.rxcui == rxcui)
    )
    result = await db.execute(stmt)
    drug = result.scalar_one_or_none()

    if drug:
        await redis_client.setex(cache_key, CACHE_TTL_DRUG, str(drug.id))
    return drug


async def get_drug_by_name(db: AsyncSession, name: str) -> Drug | None:
    stmt = (
        select(Drug)
        .options(selectinload(Drug.ingredients).selectinload(DrugIngredient.ingredient))
        .where(func.lower(Drug.name) == func.lower(name))
    )
    result = await db.execute(stmt)
    drug = result.scalar_one_or_none()

    if not drug:
        stmt = (
            select(Drug)
            .options(selectinload(Drug.ingredients).selectinload(DrugIngredient.ingredient))
            .where(func.similarity(Drug.name, name) > 0.3)
            .order_by(func.similarity(Drug.name, name).desc())
            .limit(1)
        )
        result = await db.execute(stmt)
        drug = result.scalar_one_or_none()

    return drug


async def get_cross_reactive_ingredients(db: AsyncSession, ingredient_name: str) -> list[dict]:
    stmt = (
        select(CrossReactivityGroup)
        .options(selectinload(CrossReactivityGroup.members).selectinload(CrossReactivityMember.ingredient))
        .join(CrossReactivityMember)
        .join(Ingredient)
        .where(func.lower(Ingredient.name) == func.lower(ingredient_name))
    )
    result = await db.execute(stmt)
    groups = list(result.scalars().unique().all())

    cross_reactive = []
    for group in groups:
        for member in group.members:
            if member.ingredient.name.lower() != ingredient_name.lower():
                cross_reactive.append({
                    "ingredient": member.ingredient.name,
                    "group": group.group_name,
                    "probability": member.probability,
                })
    return cross_reactive


async def get_drug_ingredients(db: AsyncSession, drug: Drug) -> list[dict]:
    ingredients = []
    for di in drug.ingredients:
        ing = di.ingredient
        ingredients.append({
            "ingredient_id": str(ing.id),
            "name": ing.name,
            "type": di.type,
            "strength": di.strength,
            "chemical_family": ing.chemical_family,
            "allergen_codes": ing.allergen_codes or [],
        })
    return ingredients
