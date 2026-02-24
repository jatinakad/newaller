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


async def get_alternative_suggestions(
    drug_name: str,
    allergen: str,
    patient_conditions: list[str] | None = None,
) -> list[dict]:
    """Use AI to suggest safe alternative drugs."""
    backend = get_ai_backend()
    conditions_text = ""
    if patient_conditions:
        conditions_text = f" The patient also has: {', '.join(patient_conditions)}."

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinical pharmacology assistant. Suggest safe drug alternatives. "
                "Return ONLY a JSON array of alternatives."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Patient is allergic to {allergen}. The prescribed drug is {drug_name}. "
                f"{conditions_text}"
                f"Suggest 2-3 safe alternative drugs that treat the same condition but "
                f"do not contain {allergen} or cross-reactive ingredients.\n"
                f'Return JSON: [{{"name": "drug name", "rxcui": "if known or empty string", '
                f'"reason": "why this is safe"}}]'
            ),
        },
    ]

    try:
        content = await backend.chat(messages, temperature=0.2, max_tokens=500)
        alternatives = _parse_json(content)
        if isinstance(alternatives, list):
            return alternatives
        return alternatives.get("alternatives", [])

    except Exception as e:
        logger.warning("ai_alternatives_failed", backend=backend.name, error=str(e))
        return []


async def check_cross_reactivity_ai(ingredient: str, allergen: str) -> dict:
    """Use AI to verify cross-reactivity between an ingredient and known allergen."""
    backend = get_ai_backend()

    messages = [
        {
            "role": "system",
            "content": (
                "You are a clinical pharmacology expert. Assess cross-reactivity risk. "
                "Return ONLY a JSON object."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Patient has a confirmed allergy to: {allergen}\n"
                f"Prescribed drug contains ingredient: {ingredient}\n"
                f"Is there cross-reactivity risk?\n"
                f'Return JSON: {{"is_cross_reactive": true/false, '
                f'"risk_level": "high/moderate/low/none", '
                f'"explanation": "brief clinical explanation"}}'
            ),
        },
    ]

    try:
        content = await backend.chat(messages, temperature=0.1, max_tokens=300)
        return _parse_json(content)

    except Exception as e:
        logger.warning("ai_cross_reactivity_failed", backend=backend.name, error=str(e))
        return {"is_cross_reactive": False, "risk_level": "unknown", "explanation": f"AI check failed: {e}"}
