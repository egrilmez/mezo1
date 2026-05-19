"""OpenAI-powered Q&A and supplier-document extraction."""
import json
import os
from typing import Optional

from openai import OpenAI

from .reference import CN_CODES, DEFAULT_EMISSIONS, REGULATION_CONTEXT


_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        _client = OpenAI(api_key=api_key)
    return _client


def _model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4o-mini")


QA_SYSTEM = f"""You are a compliance assistant specialised in the EU Carbon Border Adjustment Mechanism (CBAM).
Answer concisely (under 200 words unless detail is requested) and cite the article or annex of
Regulation (EU) 2023/956 or Implementing Regulation (EU) 2023/1773 when relevant.
If the user asks something outside CBAM scope, say so plainly.

Reference context:
{REGULATION_CONTEXT}
"""


def answer_question(question: str, conversation: list[dict] | None = None) -> str:
    client = _get_client()
    messages: list[dict] = [{"role": "system", "content": QA_SYSTEM}]
    if conversation:
        messages.extend(conversation)
    messages.append({"role": "user", "content": question})
    resp = client.chat.completions.create(model=_model(), messages=messages, temperature=0.2)
    return resp.choices[0].message.content or ""


EXTRACTION_SYSTEM = """You extract CBAM-relevant data from a supplier emissions document.
Return JSON only, matching this schema:
{
  "cn_code": "8-digit string or null",
  "description": "short product description or null",
  "country_of_origin": "ISO 3166-1 alpha-2 or null",
  "quantity": number or null,
  "quantity_unit": "tonne" | "MWh" | null,
  "production_method": "string or null",
  "installation": {
    "name": "string or null",
    "country": "ISO alpha-2 or null",
    "address": "string or null",
    "unlocode": "string or null",
    "latitude": number or null,
    "longitude": number or null
  },
  "direct_emissions_per_unit": number or null,
  "indirect_emissions_per_unit": number or null,
  "emissions_source": "actual" | "default" | "estimated",
  "carbon_price_paid": {
    "amount_eur_per_tco2": number,
    "legal_basis": "string",
    "covered_emissions_tco2": number
  } | null,
  "notes": "string with anything unclear or missing"
}

Rules:
- Emissions must be expressed per unit of good (tCO2e per tonne, or per MWh for electricity).
- If the document gives total emissions and total quantity, divide.
- If a field is not present in the document, return null (do not guess).
- "emissions_source" should be "actual" if the document reports measured/monitored values,
  "default" if it cites EU default values, otherwise "estimated".
"""


def extract_from_document(document_text: str, hint_cn_code: str | None = None) -> dict:
    client = _get_client()
    user_msg = document_text
    if hint_cn_code:
        user_msg = f"(Importer suggests CN code: {hint_cn_code})\n\n{document_text}"
    resp = client.chat.completions.create(
        model=_model(),
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    raw = resp.choices[0].message.content or "{}"
    data = json.loads(raw)
    return _enrich_with_reference(data)


def _enrich_with_reference(data: dict) -> dict:
    cn = data.get("cn_code")
    if cn and cn in CN_CODES:
        ref = CN_CODES[cn]
        data.setdefault("sector", ref["sector"])
        if not data.get("description"):
            data["description"] = ref["description"]
        if not data.get("quantity_unit"):
            data["quantity_unit"] = ref["unit"]
    if cn and cn in DEFAULT_EMISSIONS:
        defaults = DEFAULT_EMISSIONS[cn]
        if data.get("direct_emissions_per_unit") is None:
            data["direct_emissions_per_unit"] = defaults["direct"]
            data["emissions_source"] = "default"
        if data.get("indirect_emissions_per_unit") is None:
            data["indirect_emissions_per_unit"] = defaults["indirect"]
    return data
