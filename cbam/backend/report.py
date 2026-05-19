"""Generate a CBAM quarterly report XML from collected GoodEntry data.

This produces an XML structure modelled on the EU CBAM Transitional Registry quarterly
report (CBAM-QUARTERLY-REPORT). It is not byte-perfect against the official XSD — it is
intended as a working draft that mirrors the spirit and field names of the real format,
suitable for review before submission.
"""
from __future__ import annotations

from datetime import datetime, timezone
from xml.dom import minidom
from xml.etree import ElementTree as ET

from .models import GoodEntry, ReportRequest

NS = "urn:cbam:quarterlyreport:v1"


def _el(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    e = ET.SubElement(parent, f"{{{NS}}}{tag}")
    if text is not None:
        e.text = text
    return e


def _quarter_dates(year: int, quarter: int) -> tuple[str, str]:
    starts = {1: (1, 1), 2: (4, 1), 3: (7, 1), 4: (10, 1)}
    ends = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}
    sm, sd = starts[quarter]
    em, ed = ends[quarter]
    return f"{year:04d}-{sm:02d}-{sd:02d}", f"{year:04d}-{em:02d}-{ed:02d}"


def build_report(req: ReportRequest, goods: list[GoodEntry]) -> str:
    ET.register_namespace("", NS)
    root = ET.Element(f"{{{NS}}}QuarterlyReport")

    header = _el(root, "ReportHeader")
    _el(header, "ReportId", f"CBAM-{req.declarant_eori}-{req.reporting_year}Q{req.reporting_quarter}")
    _el(header, "GeneratedAt", datetime.now(timezone.utc).isoformat())
    _el(header, "ReportingYear", str(req.reporting_year))
    _el(header, "ReportingQuarter", str(req.reporting_quarter))
    start, end = _quarter_dates(req.reporting_year, req.reporting_quarter)
    _el(header, "PeriodStart", start)
    _el(header, "PeriodEnd", end)

    declarant = _el(root, "ReportingDeclarant")
    _el(declarant, "Name", req.declarant_name)
    _el(declarant, "Eori", req.declarant_eori)
    _el(declarant, "Country", req.declarant_country)

    goods_el = _el(root, "ImportedGoods")
    total_direct = 0.0
    total_indirect = 0.0
    for g in goods:
        item = _el(goods_el, "Good")
        _el(item, "CnCode", g.cn_code)
        if g.description:
            _el(item, "Description", g.description)
        if g.sector:
            _el(item, "Sector", g.sector)
        _el(item, "CountryOfOrigin", g.country_of_origin)
        qty = _el(item, "Quantity", f"{g.quantity:.6f}")
        qty.set("unit", g.quantity_unit)
        if g.production_method:
            _el(item, "ProductionMethod", g.production_method)

        if g.installation:
            inst = _el(item, "Installation")
            _el(inst, "Name", g.installation.name)
            _el(inst, "Country", g.installation.country)
            if g.installation.address:
                _el(inst, "Address", g.installation.address)
            if g.installation.unlocode:
                _el(inst, "Unlocode", g.installation.unlocode)
            if g.installation.latitude is not None and g.installation.longitude is not None:
                coords = _el(inst, "Coordinates")
                _el(coords, "Latitude", f"{g.installation.latitude:.6f}")
                _el(coords, "Longitude", f"{g.installation.longitude:.6f}")

        em = _el(item, "EmbeddedEmissions")
        em.set("source", g.emissions_source)
        direct_total = g.direct_emissions_per_unit * g.quantity
        indirect_total = g.indirect_emissions_per_unit * g.quantity
        total_direct += direct_total
        total_indirect += indirect_total
        d = _el(em, "Direct", f"{direct_total:.6f}")
        d.set("unitValue", f"{g.direct_emissions_per_unit:.6f}")
        i = _el(em, "Indirect", f"{indirect_total:.6f}")
        i.set("unitValue", f"{g.indirect_emissions_per_unit:.6f}")

        if g.carbon_price_paid:
            cp = _el(item, "CarbonPricePaid")
            _el(cp, "AmountEurPerTco2", f"{g.carbon_price_paid.amount_eur_per_tco2:.4f}")
            _el(cp, "LegalBasis", g.carbon_price_paid.legal_basis)
            _el(cp, "CoveredEmissionsTco2", f"{g.carbon_price_paid.covered_emissions_tco2:.6f}")

    totals = _el(root, "Totals")
    _el(totals, "TotalEntries", str(len(goods)))
    _el(totals, "TotalDirectEmissionsTco2", f"{total_direct:.6f}")
    _el(totals, "TotalIndirectEmissionsTco2", f"{total_indirect:.6f}")
    _el(totals, "TotalEmbeddedEmissionsTco2", f"{(total_direct + total_indirect):.6f}")

    raw = ET.tostring(root, encoding="utf-8", xml_declaration=False)
    pretty = minidom.parseString(raw).toprettyxml(indent="  ", encoding="UTF-8").decode("utf-8")
    return pretty
