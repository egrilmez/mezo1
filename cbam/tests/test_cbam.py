"""Offline tests for the CBAM tool (no OpenAI calls)."""
import json
from pathlib import Path
from xml.etree import ElementTree as ET

from fastapi.testclient import TestClient

from backend.main import app, _GOODS
from backend.models import GoodEntry, Installation, ReportRequest
from backend.report import build_report

NS = "{urn:cbam:quarterlyreport:v1}"


def _sample_good(cn="72081000"):
    return GoodEntry(
        cn_code=cn,
        description="Hot-rolled flat steel",
        sector="iron_and_steel",
        country_of_origin="TR",
        quantity=1250.0,
        quantity_unit="tonne",
        production_method="BF-BOF",
        installation=Installation(
            name="Bosporus Steel Works", country="TR",
            address="Karabuk, Turkiye", unlocode="TRKBK",
            latitude=41.205, longitude=32.6275,
        ),
        direct_emissions_per_unit=1.95,
        indirect_emissions_per_unit=0.18,
        emissions_source="actual",
    )


def test_report_xml_structure_and_totals():
    req = ReportRequest(
        reporting_year=2025, reporting_quarter=1,
        declarant_name="Acme Imports B.V.",
        declarant_eori="NL123456789012345",
        declarant_country="NL",
    )
    xml = build_report(req, [_sample_good(), _sample_good("76011000")])
    root = ET.fromstring(xml)
    assert root.tag == f"{NS}QuarterlyReport"

    totals = root.find(f"{NS}Totals")
    assert totals is not None
    assert int(totals.find(f"{NS}TotalEntries").text) == 2
    direct = float(totals.find(f"{NS}TotalDirectEmissionsTco2").text)
    # 2 entries × 1250 t × 1.95 tCO2e/t
    assert abs(direct - 2 * 1250.0 * 1.95) < 1e-6


def test_quarter_dates_in_header():
    req = ReportRequest(
        reporting_year=2025, reporting_quarter=3,
        declarant_name="X", declarant_eori="E", declarant_country="NL",
    )
    xml = build_report(req, [_sample_good()])
    root = ET.fromstring(xml)
    header = root.find(f"{NS}ReportHeader")
    assert header.find(f"{NS}PeriodStart").text == "2025-07-01"
    assert header.find(f"{NS}PeriodEnd").text == "2025-09-30"


def test_goods_crud_via_api():
    _GOODS.clear()
    client = TestClient(app)
    payload = json.loads(_sample_good().model_dump_json())
    r = client.post("/api/goods", json=payload)
    assert r.status_code == 201
    good_id = r.json()["id"]
    assert good_id

    r = client.get("/api/goods")
    assert r.status_code == 200
    assert len(r.json()) == 1

    r = client.delete(f"/api/goods/{good_id}")
    assert r.status_code == 204

    r = client.get("/api/goods")
    assert r.json() == []


def test_report_endpoint_returns_xml():
    _GOODS.clear()
    client = TestClient(app)
    client.post("/api/goods", json=json.loads(_sample_good().model_dump_json()))
    r = client.post("/api/report", json={
        "reporting_year": 2025, "reporting_quarter": 1,
        "declarant_name": "Acme", "declarant_eori": "NL123",
        "declarant_country": "NL",
    })
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/xml")
    assert "<ReportHeader>" in r.text
    assert "Content-Disposition" in r.headers


def test_reference_endpoint():
    client = TestClient(app)
    r = client.get("/api/reference")
    assert r.status_code == 200
    data = r.json()
    assert "cement" in data["sectors"]
    assert "72081000" in data["cn_codes"]


def test_sample_data_files_exist():
    base = Path(__file__).resolve().parent.parent / "sample_data"
    assert (base / "supplier_report_steel.txt").exists()
    assert (base / "supplier_report_aluminium.txt").exists()
    assert (base / "sample_quarterly_input.json").exists()
