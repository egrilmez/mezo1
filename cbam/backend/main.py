"""FastAPI app: CBAM regulation Q&A, supplier-doc extraction, goods registry, XML report."""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import ai, report
from .models import ExtractionRequest, GoodEntry, QARequest, ReportRequest
from .reference import CN_CODES, DEFAULT_EMISSIONS, REGULATION_CONTEXT, SECTORS

load_dotenv()

app = FastAPI(title="CBAM Reporting Tool", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory store. Fine for MVP; swap for a DB later.
_GOODS: dict[str, GoodEntry] = {}


@app.get("/api/health")
def health():
    return {"ok": True, "openai_configured": bool(os.getenv("OPENAI_API_KEY"))}


@app.get("/api/reference")
def reference():
    return {
        "sectors": SECTORS,
        "cn_codes": CN_CODES,
        "default_emissions": DEFAULT_EMISSIONS,
        "regulation_context": REGULATION_CONTEXT,
    }


@app.post("/api/qa")
def qa(req: QARequest):
    try:
        answer = ai.answer_question(req.question, req.conversation)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"LLM call failed: {e}")
    return {"answer": answer}


@app.post("/api/extract")
def extract(req: ExtractionRequest):
    if not req.document_text.strip():
        raise HTTPException(status_code=400, detail="document_text is empty")
    try:
        data = ai.extract_from_document(req.document_text, req.hint_cn_code)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Extraction failed: {e}")
    return data


@app.get("/api/goods")
def list_goods():
    return list(_GOODS.values())


@app.post("/api/goods", status_code=201)
def add_good(entry: GoodEntry):
    entry.id = entry.id or str(uuid.uuid4())
    if entry.cn_code in CN_CODES:
        ref = CN_CODES[entry.cn_code]
        entry.sector = entry.sector or ref["sector"]
        entry.description = entry.description or ref["description"]
    _GOODS[entry.id] = entry
    return entry


@app.delete("/api/goods/{good_id}", status_code=204)
def delete_good(good_id: str):
    if good_id not in _GOODS:
        raise HTTPException(status_code=404, detail="good not found")
    del _GOODS[good_id]
    return Response(status_code=204)


@app.post("/api/report")
def generate_report(req: ReportRequest):
    pool = list(_GOODS.values())
    if req.good_ids:
        pool = [g for g in pool if g.id in req.good_ids]
    if not pool:
        raise HTTPException(status_code=400, detail="no goods to report")
    xml = report.build_report(req, pool)
    filename = f"CBAM_{req.declarant_eori}_{req.reporting_year}Q{req.reporting_quarter}.xml"
    return Response(
        content=xml,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if _FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=_FRONTEND_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(_FRONTEND_DIR / "index.html")
