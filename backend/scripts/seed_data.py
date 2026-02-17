"""
Seed script: Populates the database with sample drug data, cross-reactivity groups,
and a demo patient for testing. Run via: python -m scripts.seed_data
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.db.session import async_session_factory, engine, Base
from app.models.drug import Drug, Ingredient, DrugIngredient, CrossReactivityGroup, CrossReactivityMember
from app.models.patient import Patient, PatientAllergy, LabSensitivity, PatientCondition
from app.models.audit import AuditLog, AuditOverride


DRUGS_DATA = [
    {
        "rxcui": "723",
        "name": "Amoxicillin 500mg Capsule",
        "generic_name": "Amoxicillin",
        "dosage_form": "Capsule",
        "route": "Oral",
        "brand_names": ["Amoxil", "Trimox"],
        "ingredients": [
            {"name": "Amoxicillin Trihydrate", "type": "active", "strength": "500 mg", "chemical_family": "Penicillin-class Beta-Lactam", "allergen_codes": ["91936005"]},
            {"name": "Magnesium Stearate", "type": "excipient"},
            {"name": "Gelatin", "type": "excipient", "allergen_codes": ["412071004"]},
        ],
    },
    {
        "rxcui": "3498",
        "name": "Cetirizine 10mg Tablet",
        "generic_name": "Cetirizine",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Zyrtec"],
        "ingredients": [
            {"name": "Cetirizine Hydrochloride", "type": "active", "strength": "10 mg", "chemical_family": "Piperazine antihistamine"},
            {"name": "Lactose Monohydrate", "type": "excipient"},
            {"name": "Microcrystalline Cellulose", "type": "excipient"},
        ],
    },
    {
        "rxcui": "18631",
        "name": "Azithromycin 500mg Tablet",
        "generic_name": "Azithromycin",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Zithromax", "Z-Pack"],
        "ingredients": [
            {"name": "Azithromycin Dihydrate", "type": "active", "strength": "500 mg", "chemical_family": "Macrolide antibiotic"},
            {"name": "Calcium Phosphate", "type": "excipient"},
        ],
    },
    {
        "rxcui": "2551",
        "name": "Ciprofloxacin 500mg Tablet",
        "generic_name": "Ciprofloxacin",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Cipro"],
        "ingredients": [
            {"name": "Ciprofloxacin Hydrochloride", "type": "active", "strength": "500 mg", "chemical_family": "Fluoroquinolone antibiotic"},
            {"name": "Microcrystalline Cellulose", "type": "excipient"},
            {"name": "Magnesium Stearate", "type": "excipient"},
        ],
    },
    {
        "rxcui": "10582",
        "name": "Ibuprofen 400mg Tablet",
        "generic_name": "Ibuprofen",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Advil", "Motrin"],
        "ingredients": [
            {"name": "Ibuprofen", "type": "active", "strength": "400 mg", "chemical_family": "NSAID (Propionic acid derivative)"},
            {"name": "Stearic Acid", "type": "excipient"},
        ],
    },
    {
        "rxcui": "7052",
        "name": "Metformin 500mg Tablet",
        "generic_name": "Metformin",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Glucophage"],
        "ingredients": [
            {"name": "Metformin Hydrochloride", "type": "active", "strength": "500 mg", "chemical_family": "Biguanide"},
            {"name": "Povidone", "type": "excipient"},
        ],
    },
    {
        "rxcui": "1191",
        "name": "Aspirin 325mg Tablet",
        "generic_name": "Aspirin",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Bayer", "Ecotrin"],
        "ingredients": [
            {"name": "Aspirin", "type": "active", "strength": "325 mg", "chemical_family": "NSAID (Salicylate)", "allergen_codes": ["387458008"]},
            {"name": "Corn Starch", "type": "excipient"},
        ],
    },
    {
        "rxcui": "1819",
        "name": "Cephalexin 500mg Capsule",
        "generic_name": "Cephalexin",
        "dosage_form": "Capsule",
        "route": "Oral",
        "brand_names": ["Keflex"],
        "ingredients": [
            {"name": "Cephalexin Monohydrate", "type": "active", "strength": "500 mg", "chemical_family": "Cephalosporin (First-generation)", "allergen_codes": ["372809001"]},
            {"name": "Magnesium Stearate", "type": "excipient"},
            {"name": "Gelatin", "type": "excipient", "allergen_codes": ["412071004"]},
        ],
    },
    {
        "rxcui": "4053",
        "name": "Hydrocortisone 1% Cream",
        "generic_name": "Hydrocortisone",
        "dosage_form": "Cream",
        "route": "Topical",
        "brand_names": ["Cortaid"],
        "ingredients": [
            {"name": "Hydrocortisone", "type": "active", "strength": "1%", "chemical_family": "Corticosteroid"},
            {"name": "Cetyl Alcohol", "type": "excipient"},
            {"name": "Propylene Glycol", "type": "excipient"},
        ],
    },
    {
        "rxcui": "36567",
        "name": "Calamine Lotion",
        "generic_name": "Calamine",
        "dosage_form": "Lotion",
        "route": "Topical",
        "brand_names": ["Caladryl"],
        "ingredients": [
            {"name": "Calamine", "type": "active", "strength": "8%", "chemical_family": "Zinc compound"},
            {"name": "Zinc Oxide", "type": "active", "strength": "8%", "chemical_family": "Zinc compound"},
            {"name": "Glycerin", "type": "excipient"},
            {"name": "Bentonite", "type": "excipient"},
        ],
    },
    {
        "rxcui": "11289",
        "name": "Sulfamethoxazole-Trimethoprim 800-160mg Tablet",
        "generic_name": "Sulfamethoxazole/Trimethoprim",
        "dosage_form": "Tablet",
        "route": "Oral",
        "brand_names": ["Bactrim", "Septra"],
        "ingredients": [
            {"name": "Sulfamethoxazole", "type": "active", "strength": "800 mg", "chemical_family": "Sulfonamide antibiotic", "allergen_codes": ["363528007"]},
            {"name": "Trimethoprim", "type": "active", "strength": "160 mg", "chemical_family": "Dihydrofolate reductase inhibitor"},
        ],
    },
    {
        "rxcui": "7804",
        "name": "Omeprazole 20mg Capsule",
        "generic_name": "Omeprazole",
        "dosage_form": "Capsule",
        "route": "Oral",
        "brand_names": ["Prilosec"],
        "ingredients": [
            {"name": "Omeprazole", "type": "active", "strength": "20 mg", "chemical_family": "Proton pump inhibitor"},
            {"name": "Gelatin", "type": "excipient", "allergen_codes": ["412071004"]},
        ],
    },
]

CROSS_REACTIVITY_GROUPS = [
    {
        "group_name": "Beta-Lactam Antibiotics",
        "members": [
            {"ingredient_name": "Amoxicillin Trihydrate", "probability": "high"},
            {"ingredient_name": "Cephalexin Monohydrate", "probability": "moderate"},
        ],
    },
    {
        "group_name": "NSAIDs",
        "members": [
            {"ingredient_name": "Ibuprofen", "probability": "moderate"},
            {"ingredient_name": "Aspirin", "probability": "moderate"},
        ],
    },
    {
        "group_name": "Sulfonamides",
        "members": [
            {"ingredient_name": "Sulfamethoxazole", "probability": "high"},
        ],
    },
]

DEMO_PATIENT = {
    "external_id": "P-5678",
    "name": "John Doe",
    "age": 45,
    "gender": "Male",
    "weight_kg": 80.0,
    "allergies": [
        {
            "allergen_code": "91936005",
            "allergen_name": "Penicillin",
            "category": "drug",
            "criticality": "high",
            "reaction_manifestations": ["Anaphylaxis", "Urticaria"],
            "reaction_severity": "severe",
            "verification_status": "confirmed",
        },
        {
            "allergen_code": "363528007",
            "allergen_name": "Sulfonamide",
            "category": "drug",
            "criticality": "high",
            "reaction_manifestations": ["Rash", "Stevens-Johnson Syndrome"],
            "reaction_severity": "severe",
            "verification_status": "confirmed",
        },
    ],
    "lab_sensitivities": [
        {
            "test_code": "6158-0",
            "test_name": "Specific IgE - Cephalosporin",
            "value": 1.2,
            "unit": "kU/L",
            "reference_range": "< 0.35",
            "interpretation": "elevated",
            "related_substances": ["Cephalexin", "Cefazolin", "Cephalexin Monohydrate"],
        },
    ],
    "conditions": [
        {
            "condition_code": "G6PD",
            "condition_name": "G6PD Deficiency",
            "contraindicated_ingredients": ["Dapsone", "Primaquine", "Nitrofurantoin", "Sulfamethoxazole"],
        },
    ],
}

DEMO_PATIENT_2 = {
    "external_id": "P-1234",
    "name": "Jane Smith",
    "age": 32,
    "gender": "Female",
    "weight_kg": 65.0,
    "allergies": [
        {
            "allergen_code": "387458008",
            "allergen_name": "Aspirin",
            "category": "drug",
            "criticality": "high",
            "reaction_manifestations": ["Bronchospasm", "Angioedema"],
            "reaction_severity": "severe",
            "verification_status": "confirmed",
        },
    ],
    "lab_sensitivities": [],
    "conditions": [],
}


async def seed():
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        # --- Seed ingredients and drugs ---
        ingredient_cache: dict[str, Ingredient] = {}

        for drug_data in DRUGS_DATA:
            # Check if drug already exists
            from sqlalchemy import select
            existing = await session.execute(
                select(Drug).where(Drug.rxcui == drug_data["rxcui"])
            )
            if existing.scalar_one_or_none():
                print(f"  Drug {drug_data['name']} already exists, skipping")
                continue

            drug = Drug(
                rxcui=drug_data["rxcui"],
                name=drug_data["name"],
                generic_name=drug_data.get("generic_name"),
                dosage_form=drug_data.get("dosage_form"),
                route=drug_data.get("route"),
                brand_names=drug_data.get("brand_names"),
                source="SEED",
            )
            session.add(drug)
            await session.flush()

            for ing_data in drug_data.get("ingredients", []):
                ing_name = ing_data["name"]
                if ing_name not in ingredient_cache:
                    existing_ing = await session.execute(
                        select(Ingredient).where(Ingredient.name == ing_name)
                    )
                    ingredient = existing_ing.scalar_one_or_none()
                    if not ingredient:
                        ingredient = Ingredient(
                            name=ing_name,
                            chemical_family=ing_data.get("chemical_family"),
                            allergen_codes=ing_data.get("allergen_codes"),
                        )
                        session.add(ingredient)
                        await session.flush()
                    ingredient_cache[ing_name] = ingredient

                di = DrugIngredient(
                    drug_id=drug.id,
                    ingredient_id=ingredient_cache[ing_name].id,
                    type=ing_data.get("type", "active"),
                    strength=ing_data.get("strength"),
                )
                session.add(di)

            print(f"  Seeded drug: {drug_data['name']}")

        await session.flush()

        # --- Seed cross-reactivity groups ---
        for group_data in CROSS_REACTIVITY_GROUPS:
            from sqlalchemy import select
            existing_group = await session.execute(
                select(CrossReactivityGroup).where(CrossReactivityGroup.group_name == group_data["group_name"])
            )
            if existing_group.scalar_one_or_none():
                print(f"  Group '{group_data['group_name']}' already exists, skipping")
                continue

            group = CrossReactivityGroup(group_name=group_data["group_name"])
            session.add(group)
            await session.flush()

            for member_data in group_data["members"]:
                ing_name = member_data["ingredient_name"]
                if ing_name in ingredient_cache:
                    member = CrossReactivityMember(
                        group_id=group.id,
                        ingredient_id=ingredient_cache[ing_name].id,
                        probability=member_data.get("probability", "moderate"),
                    )
                    session.add(member)

            print(f"  Seeded cross-reactivity group: {group_data['group_name']}")

        await session.flush()

        # --- Seed demo patients ---
        for patient_data in [DEMO_PATIENT, DEMO_PATIENT_2]:
            from sqlalchemy import select
            existing_patient = await session.execute(
                select(Patient).where(Patient.external_id == patient_data["external_id"])
            )
            if existing_patient.scalar_one_or_none():
                print(f"  Patient '{patient_data['name']}' already exists, skipping")
                continue

            patient = Patient(
                external_id=patient_data["external_id"],
                name=patient_data["name"],
                age=patient_data.get("age"),
                gender=patient_data.get("gender"),
                weight_kg=patient_data.get("weight_kg"),
            )
            session.add(patient)
            await session.flush()

            for allergy_data in patient_data.get("allergies", []):
                allergy = PatientAllergy(
                    patient_id=patient.id,
                    allergen_code=allergy_data.get("allergen_code"),
                    allergen_name=allergy_data["allergen_name"],
                    category=allergy_data.get("category", "drug"),
                    criticality=allergy_data.get("criticality", "high"),
                    reaction_manifestations=allergy_data.get("reaction_manifestations"),
                    reaction_severity=allergy_data.get("reaction_severity"),
                    verification_status=allergy_data.get("verification_status", "confirmed"),
                )
                session.add(allergy)

            for lab_data in patient_data.get("lab_sensitivities", []):
                lab = LabSensitivity(
                    patient_id=patient.id,
                    test_code=lab_data.get("test_code"),
                    test_name=lab_data["test_name"],
                    value=lab_data["value"],
                    unit=lab_data["unit"],
                    reference_range=lab_data.get("reference_range"),
                    interpretation=lab_data.get("interpretation", "normal"),
                    related_substances=lab_data.get("related_substances"),
                )
                session.add(lab)

            for cond_data in patient_data.get("conditions", []):
                cond = PatientCondition(
                    patient_id=patient.id,
                    condition_code=cond_data.get("condition_code"),
                    condition_name=cond_data["condition_name"],
                    contraindicated_ingredients=cond_data.get("contraindicated_ingredients"),
                )
                session.add(cond)

            print(f"  Seeded patient: {patient_data['name']}")

        await session.commit()
        print("\nSeed complete!")


if __name__ == "__main__":
    print("Seeding MedGuard database...")
    asyncio.run(seed())
