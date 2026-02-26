import json
import base64
import structlog
from app.core.ai_backends import get_ai_backend

logger = structlog.get_logger()


def _parse_json(content: str) -> dict | list:
    """Extract and parse JSON from an LLM response that may contain markdown fences."""
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()
    return json.loads(content)


async def extract_drugs_from_image(image_bytes: bytes) -> dict:
    """Use AI (MedGemma / any configured backend) to extract drug names from a prescription photo."""
    backend = get_ai_backend()
    b64_image = base64.b64encode(image_bytes).decode("utf-8")

    prompt = (
        "You are a medical prescription reader. Extract ALL medicine names, "
        "dosages, and forms from this prescription image. "
        "Return ONLY a JSON object with this exact format:\n"
        '{"drugs": [{"name": "medicine name", "dosage": "dosage if visible", "form": "tablet/syrup/lotion/etc"}], '
        '"confidence": 0.0 to 1.0}\n'
        "If you cannot read the prescription clearly, set confidence below 0.5."
    )

    try:
        if backend.supports_vision:
            content = await backend.chat_with_image(prompt, b64_image, temperature=0.1, max_tokens=1000)
        else:
            logger.warning("ai_vision_not_supported", backend=backend.name)
            return {"drugs": [], "confidence": 0.0, "error": f"Backend '{backend.name}' does not support vision/OCR"}

        return _parse_json(content)

    except Exception as e:
        logger.error("ai_ocr_failed", backend=backend.name, error=str(e))
        return {"drugs": [], "confidence": 0.0, "error": str(e)}


async def analyze_prescription(
    medicine_names: list[str],
    patient_allergies: list[dict],
    patient_conditions: list[dict],
    patient_lab_sensitivities: list[dict],
    report_text: str = "",
    web_drug_context: str = "",
) -> dict:
    """
    Single comprehensive LLM call that checks all medicines against patient profile.
    MedGemma reasons over ingredients, cross-reactivity, contraindications — all at once.
    Returns structured JSON with signals, warnings, alternatives, and needs_verification list.
    """
    backend = get_ai_backend()

    # Build patient context
    allergy_lines = []
    for a in patient_allergies:
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
    for c in patient_conditions:
        line = f"- {c.get('condition_name', 'Unknown')}"
        if c.get("contraindicated_ingredients"):
            line += f" (avoid: {', '.join(c['contraindicated_ingredients'])})"
        condition_lines.append(line)
    condition_text = "\n".join(condition_lines) if condition_lines else "None known"

    lab_lines = []
    for ls in patient_lab_sensitivities:
        line = f"- {ls.get('test_name', 'Unknown')}: {ls.get('value', '')} {ls.get('unit', '')} ({ls.get('interpretation', 'normal')})"
        if ls.get("reference_range"):
            line += f" [ref: {ls['reference_range']}]"
        if ls.get("related_substances"):
            line += f" — related to: {', '.join(ls['related_substances'])}"
        lab_lines.append(line)
    lab_text = "\n".join(lab_lines) if lab_lines else "None"

    report_section = ""
    if report_text:
        # Truncate to keep within token limits
        truncated = report_text[:3000]
        report_section = f"\nPATIENT REPORT EXCERPTS:\n{truncated}\n"

    web_section = ""
    if web_drug_context:
        web_section = f"\nDRUG REFERENCE DATA (from FDA/DailyMed):\n{web_drug_context}\n"

    medicines_text = "\n".join(f"- {m}" for m in medicine_names)

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinical pharmacology expert and allergy specialist. "
                "Your job is to check prescribed medicines against a patient's allergy profile "
                "for safety. You must check ALL ingredients — both active AND inactive/excipients. "
                "You must also check for cross-reactivity between drug families. "
                "Be thorough but precise. Only flag real clinical risks, not theoretical ones.\n\n"
                "IMPORTANT: For each drug AND each warning, provide detailed 'reasoning' that explains "
                "your clinical rationale step-by-step: which specific ingredients are problematic, "
                "what the cross-reactivity mechanism is, and reference any relevant data from the "
                "patient reports or lab values. The reasoning should be 2-4 sentences.\n\n"
                "Return ONLY valid JSON, no other text."
            ),
        },
        {
            "role": "user",
            "content": (
                f"PATIENT ALLERGIES:\n{allergy_text}\n\n"
                f"PATIENT CONDITIONS:\n{condition_text}\n\n"
                f"PATIENT LAB VALUES:\n{lab_text}\n"
                f"{report_section}"
                f"{web_section}\n"
                f"PRESCRIBED MEDICINES:\n{medicines_text}\n\n"
                "For EACH medicine, analyze:\n"
                "1. All known ingredients (active + inactive/excipients) — do any match patient allergens?\n"
                "2. Cross-reactivity — is the medicine in the same drug family as a known allergen?\n"
                "3. Condition contraindications — is the medicine unsafe given patient conditions?\n"
                "4. Lab value concerns — do any abnormal lab values make this medicine risky?\n"
                "5. Any relevant info from patient reports if provided.\n\n"
                "If you are NOT CERTAIN about a specific ingredient or cross-reactivity, "
                "include it in needs_verification so I can look it up from FDA/DailyMed.\n\n"
                "Return this exact JSON structure:\n"
                "{\n"
                '  "drug_results": [\n'
                "    {\n"
                '      "drug_name": "medicine name",\n'
                '      "signal": "RED" or "YELLOW" or "GREEN",\n'
                '      "reasoning": "detailed 2-4 sentence explanation of why this signal was given, referencing specific ingredients, patient allergies, report data, and clinical evidence",\n'
                '      "warnings": [\n'
                "        {\n"
                '          "severity": "CRITICAL" or "HIGH" or "MODERATE" or "LOW",\n'
                '          "type": "DIRECT_MATCH" or "CROSS_REACTIVITY" or "CONTRAINDICATION" or "LAB_CONCERN",\n'
                '          "ingredient": "ingredient causing the issue",\n'
                '          "allergen": "patient allergen it conflicts with",\n'
                '          "message": "clear explanation of the risk",\n'
                '          "reasoning": "detailed clinical reasoning: what the ingredient is, how it relates to the allergen, mechanism of reaction, and any supporting evidence from patient reports or lab values"\n'
                "        }\n"
                "      ],\n"
                '      "alternatives": [\n'
                "        {\n"
                '          "name": "safe alternative drug name",\n'
                '          "reason": "why this is safe for this patient"\n'
                "        }\n"
                "      ]\n"
                "    }\n"
                "  ],\n"
                '  "needs_verification": ["drug names where you need more data to be certain"]\n'
                "}"
            ),
        },
    ]

    try:
        content = await backend.chat(messages, temperature=0.1, max_tokens=4000)
        result = _parse_json(content)
        if isinstance(result, dict):
            return result
        return {"drug_results": [], "needs_verification": []}

    except Exception as e:
        logger.error("ai_analyze_prescription_failed", backend=backend.name, error=str(e))
        return {"drug_results": [], "needs_verification": medicine_names, "error": str(e)}