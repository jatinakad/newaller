import structlog
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.ai_backends import get_ai_backend
from app.core import patient_service, report_service

logger = structlog.get_logger()


async def ask_about_patient(
    db: AsyncSession,
    patient_id: str,
    question: str,
    medicine_name: str = "",
    conversation_history: list[dict] | None = None,
) -> dict:
    """
    Doctor asks a free-form question about a patient's data.
    The AI receives full patient context (allergies, conditions, labs, reports)
    and answers with clinical reasoning.
    """
    backend = get_ai_backend()

    # Gather patient context
    profile = await patient_service.get_allergy_profile(db, patient_id)
    if not profile:
        return {"answer": "Patient not found.", "error": True}

    patient_obj = await patient_service.get_patient_by_external_id(db, patient_id)
    report_text = ""
    if patient_obj:
        report_text = await report_service.get_all_report_texts(db, patient_obj.id)

    # Build context
    allergy_lines = []
    for a in profile.get("known_allergens", []):
        line = f"- {a.get('allergen_name', 'Unknown')}"
        if a.get("criticality"):
            line += f" (criticality: {a['criticality']})"
        if a.get("reaction_manifestations"):
            line += f" — reactions: {', '.join(a['reaction_manifestations'])}"
        if a.get("reaction_severity"):
            line += f" — severity: {a['reaction_severity']}"
        allergy_lines.append(line)
    allergy_text = "\n".join(allergy_lines) if allergy_lines else "None known"

    condition_lines = []
    for c in profile.get("conditions", []):
        line = f"- {c.get('condition_name', 'Unknown')}"
        if c.get("contraindicated_ingredients"):
            line += f" (avoid: {', '.join(c['contraindicated_ingredients'])})"
        condition_lines.append(line)
    condition_text = "\n".join(condition_lines) if condition_lines else "None known"

    lab_lines = []
    for ls in profile.get("lab_sensitivities", []):
        line = f"- {ls.get('test_name', 'Unknown')}: {ls.get('value', '')} {ls.get('unit', '')} ({ls.get('interpretation', 'normal')})"
        if ls.get("reference_range"):
            line += f" [ref: {ls['reference_range']}]"
        if ls.get("related_substances"):
            line += f" — related to: {', '.join(ls['related_substances'])}"
        lab_lines.append(line)
    lab_text = "\n".join(lab_lines) if lab_lines else "None"

    report_section = ""
    if report_text:
        truncated = report_text[:4000]
        report_section = f"\nPATIENT REPORTS / MEDICAL DOCUMENTS:\n{truncated}\n"

    medicine_section = ""
    if medicine_name:
        medicine_section = f"\nMEDICINE IN QUESTION: {medicine_name}\n"

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinical pharmacology expert and allergy prevention specialist. "
                "You have access to a patient's complete medical profile including their allergies, "
                "conditions, lab values, and uploaded medical reports/documents. "
                "Answer the doctor's questions accurately based on the available patient data. "
                "If the question is about a specific medicine, analyze whether it is safe for this patient "
                "considering their allergy profile, conditions, and lab values. "
                "Always provide clinical reasoning and cite which specific patient data points support your answer. "
                "If you are uncertain, clearly state your level of confidence and recommend further verification."
            ),
        },
        {
            "role": "user",
            "content": (
                f"PATIENT: {profile.get('name', 'Unknown')} (ID: {profile.get('external_id', '')})\n"
                f"Age: {profile.get('age', 'N/A')} | Gender: {profile.get('gender', 'N/A')}\n\n"
                f"KNOWN ALLERGIES:\n{allergy_text}\n\n"
                f"CONDITIONS:\n{condition_text}\n\n"
                f"LAB VALUES:\n{lab_text}\n"
                f"{report_section}"
                f"{medicine_section}\n"
                f"DOCTOR'S QUESTION: {question}"
            ),
        },
    ]

    # Add conversation history if provided
    if conversation_history:
        # Insert history before the current question
        current_question = messages.pop()
        for hist in conversation_history[-10:]:  # Last 10 messages max
            messages.append(hist)
        messages.append(current_question)

    try:
        answer = await backend.chat(messages, temperature=0.3, max_tokens=2000)
        return {
            "answer": answer,
            "patient_name": profile.get("name", "Unknown"),
            "patient_id": profile.get("external_id", ""),
            "context_used": {
                "allergies_count": len(profile.get("known_allergens", [])),
                "conditions_count": len(profile.get("conditions", [])),
                "lab_values_count": len(profile.get("lab_sensitivities", [])),
                "reports_available": bool(report_text),
            },
            "error": False,
        }
    except Exception as e:
        logger.error("chat_failed", error=str(e))
        return {"answer": f"AI analysis failed: {str(e)}", "error": True}
