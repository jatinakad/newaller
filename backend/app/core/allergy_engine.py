import uuid
import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import ai_service, report_service, web_search, patient_service
from app.core.ai_backends import get_ai_backend
from app.schemas.prescription import Warning, DrugCheckResult, AlternativeDrug, Citation

logger = structlog.get_logger()


async def check_prescription(
    db: AsyncSession,
    patient_id: str,
    medicine_names: list[str],
) -> dict:
    """
    LLM-first allergy check. Sends all medicines + full patient context to MedGemma
    in a single call. If the LLM is uncertain about any drug, fetches data from
    OpenFDA/DailyMed and retries with citations.

    Returns dict with: overall_signal, drug_results, citations
    """
    # 1. Fetch full patient profile
    profile = await patient_service.get_allergy_profile(db, patient_id)
    if not profile:
        return None

    allergies = profile.get("known_allergens", [])
    conditions = profile.get("conditions", [])
    lab_sensitivities = profile.get("lab_sensitivities", [])

    # 2. Get any uploaded report text for this patient
    patient_obj = await patient_service.get_patient_by_external_id(db, patient_id)
    report_text = ""
    if patient_obj:
        report_text = await report_service.get_all_report_texts(db, patient_obj.id)

    # 3. First pass: ask MedGemma to analyze
    ai_result = await ai_service.analyze_prescription(
        medicine_names=medicine_names,
        patient_allergies=allergies,
        patient_conditions=conditions,
        patient_lab_sensitivities=lab_sensitivities,
        report_text=report_text,
    )

    # 4. If LLM needs verification — fetch from OpenFDA/DailyMed and retry
    all_citations = []
    needs_verification = ai_result.get("needs_verification", [])

    if needs_verification:
        logger.info("fetching_web_data_for_verification", drugs=needs_verification)
        web_context_parts = []
        for drug_name in needs_verification:
            info = await web_search.get_drug_info_with_citations(drug_name)
            if info.get("context"):
                web_context_parts.append(f"=== {drug_name} ===\n{info['context']}")
            all_citations.extend(info.get("citations", []))

        if web_context_parts:
            web_drug_context = "\n\n".join(web_context_parts)
            # Retry with web data
            ai_result = await ai_service.analyze_prescription(
                medicine_names=medicine_names,
                patient_allergies=allergies,
                patient_conditions=conditions,
                patient_lab_sensitivities=lab_sensitivities,
                report_text=report_text,
                web_drug_context=web_drug_context,
            )

    # 5. Parse AI results into structured response
    drug_results: list[DrugCheckResult] = []
    for dr in ai_result.get("drug_results", []):
        warnings = []
        for w in dr.get("warnings", []):
            warnings.append(Warning(
                warning_id=f"W-{uuid.uuid4().hex[:8]}",
                severity=w.get("severity", "MODERATE"),
                type=w.get("type", "AI_ANALYSIS"),
                ingredient=w.get("ingredient", ""),
                allergen=w.get("allergen", ""),
                message=w.get("message", ""),
                reasoning=w.get("reasoning", ""),
                evidence={
                    "source": "AI_ANALYSIS",
                    "detail": f"MedGemma ({get_ai_backend().name})",
                },
            ))

        alternatives = []
        for alt in dr.get("alternatives", [])[:3]:
            alternatives.append(AlternativeDrug(
                rxcui=alt.get("rxcui", ""),
                name=alt.get("name", "Unknown"),
                reason=alt.get("reason", "AI-suggested alternative"),
                signal="GREEN",
            ))

        drug_results.append(DrugCheckResult(
            drug={"rxcui": "", "name": dr.get("drug_name", "Unknown")},
            signal=dr.get("signal", "YELLOW"),
            reasoning=dr.get("reasoning", ""),
            warnings=warnings,
            alternatives=alternatives,
        ))

    # 6. Determine overall signal
    signals = [r.signal for r in drug_results]
    if "RED" in signals:
        overall_signal = "RED"
    elif "YELLOW" in signals:
        overall_signal = "YELLOW"
    else:
        overall_signal = "GREEN"

    # 7. Build citation objects
    citation_objects = [
        Citation(source=c["source"], url=c["url"]) for c in all_citations
    ]

    return {
        "overall_signal": overall_signal,
        "drug_results": drug_results,
        "citations": citation_objects,
    }