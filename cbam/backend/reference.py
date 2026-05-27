"""CBAM reference data: covered sectors, sample CN codes, illustrative default emissions, regulation context."""

# Six sectors in scope of Regulation (EU) 2023/956.
SECTORS = ["cement", "iron_and_steel", "aluminium", "fertilizers", "hydrogen", "electricity"]

# A small sample of CN (Combined Nomenclature) codes within CBAM scope.
# Real list is in Annex I of Reg. (EU) 2023/956; this is a working subset for the MVP.
CN_CODES = {
    "25232100": {"sector": "cement", "description": "White cement, whether or not artificially coloured", "unit": "tonne"},
    "25232900": {"sector": "cement", "description": "Other Portland cement", "unit": "tonne"},
    "72061000": {"sector": "iron_and_steel", "description": "Pig iron in primary forms", "unit": "tonne"},
    "72081000": {"sector": "iron_and_steel", "description": "Flat-rolled iron/steel, hot-rolled, in coils, with patterns in relief", "unit": "tonne"},
    "72142000": {"sector": "iron_and_steel", "description": "Bars and rods of iron/non-alloy steel, containing indentations", "unit": "tonne"},
    "76011000": {"sector": "aluminium", "description": "Unwrought aluminium, not alloyed", "unit": "tonne"},
    "76012000": {"sector": "aluminium", "description": "Unwrought aluminium alloys", "unit": "tonne"},
    "31021000": {"sector": "fertilizers", "description": "Urea, whether or not in aqueous solution", "unit": "tonne"},
    "31023000": {"sector": "fertilizers", "description": "Ammonium nitrate, whether or not in aqueous solution", "unit": "tonne"},
    "28041000": {"sector": "hydrogen", "description": "Hydrogen", "unit": "tonne"},
    "27160000": {"sector": "electricity", "description": "Electrical energy", "unit": "MWh"},
}

# Illustrative default embedded-emissions values (tCO2e per tonne, or per MWh for electricity).
# These are placeholders to seed the MVP; real defaults are published in Implementing Reg. (EU) 2023/1773
# and updated by the Commission. Replace with the official table before production use.
DEFAULT_EMISSIONS = {
    "25232100": {"direct": 0.85, "indirect": 0.05},
    "25232900": {"direct": 0.81, "indirect": 0.05},
    "72061000": {"direct": 2.10, "indirect": 0.20},
    "72081000": {"direct": 2.00, "indirect": 0.18},
    "72142000": {"direct": 1.10, "indirect": 0.15},
    "76011000": {"direct": 1.50, "indirect": 15.00},
    "76012000": {"direct": 1.60, "indirect": 14.50},
    "31021000": {"direct": 1.80, "indirect": 0.30},
    "31023000": {"direct": 1.40, "indirect": 0.25},
    "28041000": {"direct": 9.00, "indirect": 1.50},
    "27160000": {"direct": 0.00, "indirect": 0.42},
}


REGULATION_CONTEXT = """
CBAM = Carbon Border Adjustment Mechanism (Regulation (EU) 2023/956).

Timeline:
- Transitional phase: 1 Oct 2023 – 31 Dec 2025. Importers (or indirect customs reps) file
  a CBAM quarterly report; no financial obligation yet.
- Definitive phase: from 1 Jan 2026. Authorised CBAM declarants must surrender CBAM
  certificates corresponding to embedded emissions of imported CBAM goods, less any
  carbon price already paid in the country of origin.

In-scope sectors (Annex I): cement, electricity, fertilizers, iron and steel,
aluminium, hydrogen, plus certain precursors and downstream products.

Quarterly report (transitional) – deadline: end of the month following the quarter end
(e.g. Q1 report due 30 April). Submitted via the CBAM Transitional Registry.

Per-good data required:
- CN code (8 digits) and quantity imported
- Country of origin
- Installation that produced the good (name, address, UNLOCODE, geo coords)
- Production route / method
- Embedded direct emissions (tCO2e per unit)
- Embedded indirect emissions (tCO2e per unit) – mandatory for cement/fertilizers,
  optional for steel/aluminium/hydrogen during transition
- Carbon price effectively paid in the country of origin (if any), with legal basis

From Q3 2024 onward only "actual" embedded emissions may be reported; default values
are accepted only in limited cases (≤20% of total embedded emissions of complex goods).

Penalties for non-compliance during transition: EUR 10–50 per tonne of unreported
embedded emissions, applied by the competent authority of the importer's Member State.
"""
