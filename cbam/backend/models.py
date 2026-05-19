from typing import Optional, Literal
from pydantic import BaseModel, Field


class Installation(BaseModel):
    name: str
    country: str = Field(description="ISO 3166-1 alpha-2 country code, e.g. 'TR', 'CN'")
    address: Optional[str] = None
    unlocode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class CarbonPricePaid(BaseModel):
    amount_eur_per_tco2: float
    legal_basis: str
    covered_emissions_tco2: float


class GoodEntry(BaseModel):
    id: Optional[str] = None
    cn_code: str = Field(description="8-digit CN (Combined Nomenclature) code")
    description: Optional[str] = None
    sector: Optional[str] = None
    country_of_origin: str = Field(description="ISO 3166-1 alpha-2")
    quantity: float = Field(description="Tonnes (or MWh for electricity)")
    quantity_unit: Literal["tonne", "MWh"] = "tonne"
    production_method: Optional[str] = None
    installation: Optional[Installation] = None
    direct_emissions_per_unit: float = Field(description="tCO2e per unit")
    indirect_emissions_per_unit: float = Field(description="tCO2e per unit")
    emissions_source: Literal["actual", "default", "estimated"] = "actual"
    carbon_price_paid: Optional[CarbonPricePaid] = None
    import_date: Optional[str] = None


class ExtractionRequest(BaseModel):
    document_text: str
    hint_cn_code: Optional[str] = None


class QARequest(BaseModel):
    question: str
    conversation: list[dict] = Field(default_factory=list)


class ReportRequest(BaseModel):
    reporting_year: int
    reporting_quarter: Literal[1, 2, 3, 4]
    declarant_name: str
    declarant_eori: str = Field(description="EORI number of the reporting declarant")
    declarant_country: str = Field(description="ISO 3166-1 alpha-2")
    good_ids: Optional[list[str]] = None
