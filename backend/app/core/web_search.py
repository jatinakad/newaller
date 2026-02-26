import structlog
import httpx
from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

DAILYMED_API = "https://dailymed.nlm.nih.gov/dailymed/services/v2"
OPENFDA_API = settings.OPENFDA_API_URL


async def search_openfda_drug(drug_name: str) -> dict | None:
    """Search OpenFDA for drug label info (ingredients, warnings, contraindications)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{OPENFDA_API}/label.json",
                params={
                    "search": f'openfda.brand_name:"{drug_name}" OR openfda.generic_name:"{drug_name}"',
                    "limit": 1,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("results", [])
                if results:
                    label = results[0]
                    return {
                        "source": "OpenFDA",
                        "url": f"https://api.fda.gov/drug/label.json?search=openfda.brand_name:{drug_name}",
                        "brand_name": _first(label.get("openfda", {}).get("brand_name", [])),
                        "generic_name": _first(label.get("openfda", {}).get("generic_name", [])),
                        "active_ingredients": label.get("active_ingredient", []),
                        "inactive_ingredients": label.get("inactive_ingredient", []),
                        "warnings": label.get("warnings", []),
                        "contraindications": label.get("contraindications", []),
                        "drug_interactions": label.get("drug_interactions", []),
                        "adverse_reactions": label.get("adverse_reactions", []),
                    }
    except Exception as e:
        logger.warning("openfda_search_failed", drug=drug_name, error=str(e))
    return None


async def search_dailymed_drug(drug_name: str) -> dict | None:
    """Search DailyMed for drug SPL (Structured Product Labeling) info."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Search for the drug
            resp = await client.get(
                f"{DAILYMED_API}/spls.json",
                params={"drug_name": drug_name, "pagesize": 1},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", [])
                if results:
                    spl = results[0]
                    set_id = spl.get("setid", "")
                    return {
                        "source": "DailyMed (NIH)",
                        "url": f"https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid={set_id}",
                        "title": spl.get("title", ""),
                        "set_id": set_id,
                    }
    except Exception as e:
        logger.warning("dailymed_search_failed", drug=drug_name, error=str(e))
    return None


async def get_drug_info_with_citations(drug_name: str) -> dict:
    """
    Fetch drug info from OpenFDA and DailyMed.
    Returns a dict with ingredient info, warnings, and citation URLs.
    """
    citations = []
    drug_context = ""

    # Try OpenFDA first (most detailed)
    fda_data = await search_openfda_drug(drug_name)
    if fda_data:
        citations.append({
            "source": fda_data["source"],
            "url": fda_data["url"],
        })
        parts = []
        if fda_data.get("active_ingredients"):
            parts.append(f"Active ingredients: {'; '.join(fda_data['active_ingredients'][:3])}")
        if fda_data.get("inactive_ingredients"):
            parts.append(f"Inactive ingredients: {'; '.join(fda_data['inactive_ingredients'][:3])}")
        if fda_data.get("warnings"):
            # Truncate warnings text to keep prompt manageable
            warn_text = fda_data["warnings"][0][:500] if fda_data["warnings"] else ""
            parts.append(f"Warnings: {warn_text}")
        if fda_data.get("contraindications"):
            contra_text = fda_data["contraindications"][0][:500] if fda_data["contraindications"] else ""
            parts.append(f"Contraindications: {contra_text}")
        if fda_data.get("adverse_reactions"):
            adv_text = fda_data["adverse_reactions"][0][:500] if fda_data["adverse_reactions"] else ""
            parts.append(f"Adverse reactions: {adv_text}")
        drug_context = "\n".join(parts)

    # Also get DailyMed link for citation
    dailymed_data = await search_dailymed_drug(drug_name)
    if dailymed_data:
        citations.append({
            "source": dailymed_data["source"],
            "url": dailymed_data["url"],
        })

    return {
        "drug_name": drug_name,
        "context": drug_context,
        "citations": citations,
    }


def _first(lst: list, default: str = "") -> str:
    return lst[0] if lst else default