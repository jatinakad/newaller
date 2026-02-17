import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import drug_service, ai_service
from app.schemas.prescription import Warning, DrugCheckResult, AlternativeDrug

logger = structlog.get_logger()


async def check_drug_against_profile(
    db: AsyncSession,
    drug_info: dict,
    ingredients: list[dict],
    allergy_profile: dict,
) -> DrugCheckResult:
    """
    Core allergy matching logic. Checks a single drug's ingredients against a patient's
    allergy profile using a layered approach:
      Layer 1: Deterministic direct match (allergen name ↔ ingredient/chemical family)
      Layer 2: Cross-reactivity from DB
      Layer 3: Lab-based sensitivities
      Layer 4: Condition contraindications
      Layer 5: AI-augmented cross-reactivity check (MedGemma)
    """
    warnings: list[Warning] = []
    signal = "GREEN"

    known_allergens = allergy_profile.get("known_allergens", [])
    lab_sensitivities = allergy_profile.get("lab_sensitivities", [])
    conditions = allergy_profile.get("conditions", [])

    allergen_names_lower = {a["allergen_name"].lower() for a in known_allergens}

    for ing in ingredients:
        ing_name = ing["name"]
        ing_name_lower = ing_name.lower()
        chemical_family = (ing.get("chemical_family") or "").lower()

        # --- LAYER 1: Direct allergen match ---
        for allergen in known_allergens:
            allergen_name_lower = allergen["allergen_name"].lower()

            is_direct_match = (
                allergen_name_lower in ing_name_lower
                or ing_name_lower in allergen_name_lower
                or (chemical_family and allergen_name_lower in chemical_family)
            )

            if is_direct_match:
                severity = "CRITICAL" if allergen.get("criticality") == "high" else "HIGH"
                manifestations = allergen.get("reaction_manifestations", [])
                manifest_text = f" History of: {', '.join(manifestations)}." if manifestations else ""

                warnings.append(Warning(
                    warning_id=f"W-{uuid.uuid4().hex[:8]}",
                    severity=severity,
                    type="DIRECT_ALLERGEN_MATCH",
                    ingredient=ing_name,
                    allergen=allergen["allergen_name"],
                    message=(
                        f"{ing_name} matches known allergen '{allergen['allergen_name']}' "
                        f"(criticality: {allergen.get('criticality', 'unknown')}).{manifest_text}"
                    ),
                    evidence={
                        "source": "EHR_ALLERGY",
                        "detail": f"Allergen: {allergen['allergen_name']}, "
                                  f"status: {allergen.get('verification_status', 'confirmed')}, "
                                  f"severity: {allergen.get('reaction_severity', 'unknown')}",
                    },
                ))
                signal = "RED"
                break

        # --- LAYER 2: Cross-reactivity from DB ---
        if signal != "RED":
            cross_reactive = await drug_service.get_cross_reactive_ingredients(db, ing_name)
            for cr in cross_reactive:
                cr_ingredient_lower = cr["ingredient"].lower()
                if cr_ingredient_lower in allergen_names_lower or any(
                    cr_ingredient_lower in a.lower() for a in allergen_names_lower
                ):
                    prob = cr.get("probability", "moderate")
                    sev = "CRITICAL" if prob == "high" else "HIGH" if prob == "moderate" else "MODERATE"
                    warnings.append(Warning(
                        warning_id=f"W-{uuid.uuid4().hex[:8]}",
                        severity=sev,
                        type="CROSS_REACTIVITY",
                        ingredient=ing_name,
                        allergen=cr["ingredient"],
                        message=(
                            f"{ing_name} belongs to cross-reactivity group '{cr['group']}'. "
                            f"Patient is allergic to {cr['ingredient']} "
                            f"(cross-reactivity probability: {prob})."
                        ),
                        evidence={
                            "source": "CROSS_REACTIVITY_DB",
                            "detail": f"Group: {cr['group']}, probability: {prob}",
                        },
                    ))
                    if prob == "high":
                        signal = "RED"
                    elif signal != "RED":
                        signal = "YELLOW"

        # --- LAYER 3: Lab-based sensitivities ---
        for lab in lab_sensitivities:
            if lab.get("interpretation") in ("elevated", "high"):
                related = [s.lower() for s in (lab.get("related_substances") or [])]
                if ing_name_lower in related or any(ing_name_lower in r for r in related):
                    warnings.append(Warning(
                        warning_id=f"W-{uuid.uuid4().hex[:8]}",
                        severity="HIGH",
                        type="LAB_SENSITIVITY",
                        ingredient=ing_name,
                        allergen=lab["test_name"],
                        message=(
                            f"Patient has {lab['interpretation']} {lab['test_name']} "
                            f"({lab['value']} {lab['unit']}, ref: {lab.get('reference_range', 'N/A')}). "
                            f"Ingredient {ing_name} is related."
                        ),
                        evidence={
                            "source": "LAB_REPORT",
                            "detail": f"{lab['test_name']}: {lab['value']} {lab['unit']}",
                        },
                    ))
                    if signal != "RED":
                        signal = "YELLOW"

        # --- LAYER 4: Condition contraindications ---
        for cond in conditions:
            contraindicated = [c.lower() for c in (cond.get("contraindicated_ingredients") or [])]
            if ing_name_lower in contraindicated:
                warnings.append(Warning(
                    warning_id=f"W-{uuid.uuid4().hex[:8]}",
                    severity="CRITICAL",
                    type="CONDITION_CONTRAINDICATION",
                    ingredient=ing_name,
                    allergen=cond["condition_name"],
                    message=(
                        f"{ing_name} is contraindicated for patient's condition: "
                        f"{cond['condition_name']}."
                    ),
                    evidence={
                        "source": "CONDITION",
                        "detail": f"Condition: {cond['condition_name']} ({cond.get('condition_code', 'N/A')})",
                    },
                ))
                signal = "RED"

    # --- LAYER 5: AI-augmented cross-reactivity (only if no RED from deterministic checks) ---
    if signal == "GREEN" and known_allergens:
        try:
            for ing in ingredients:
                if ing.get("type") == "active":
                    for allergen in known_allergens:
                        ai_result = await ai_service.check_cross_reactivity_ai(
                            ing["name"], allergen["allergen_name"]
                        )
                        if ai_result.get("is_cross_reactive") and ai_result.get("risk_level") in ("high", "moderate"):
                            warnings.append(Warning(
                                warning_id=f"W-{uuid.uuid4().hex[:8]}",
                                severity="MODERATE",
                                type="CROSS_REACTIVITY",
                                ingredient=ing["name"],
                                allergen=allergen["allergen_name"],
                                message=(
                                    f"[AI-detected] Possible cross-reactivity between {ing['name']} "
                                    f"and {allergen['allergen_name']}: {ai_result.get('explanation', '')}"
                                ),
                                evidence={
                                    "source": "AI_ANALYSIS",
                                    "detail": f"MedGemma risk: {ai_result.get('risk_level', 'unknown')}",
                                },
                            ))
                            signal = "YELLOW"
        except Exception as e:
            logger.warning("ai_cross_reactivity_check_skipped", error=str(e))

    # --- Get alternative suggestions if RED ---
    alternatives: list[AlternativeDrug] = []
    if signal == "RED":
        try:
            condition_names = [c["condition_name"] for c in conditions]
            allergen_names = [a["allergen_name"] for a in known_allergens]
            ai_alternatives = await ai_service.get_alternative_suggestions(
                drug_info.get("name", ""),
                ", ".join(allergen_names),
                condition_names if condition_names else None,
            )
            for alt in ai_alternatives[:3]:
                alternatives.append(AlternativeDrug(
                    rxcui=alt.get("rxcui", ""),
                    name=alt.get("name", "Unknown"),
                    reason=alt.get("reason", "AI-suggested alternative"),
                    signal="GREEN",
                ))
        except Exception as e:
            logger.warning("ai_alternatives_skipped", error=str(e))

    return DrugCheckResult(
        drug={"rxcui": drug_info.get("rxcui", ""), "name": drug_info.get("name", "")},
        signal=signal,
        warnings=warnings,
        alternatives=alternatives,
    )
