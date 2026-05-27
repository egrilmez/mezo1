# CBAM Reporting Tool

AI-assisted assistant for the EU **Carbon Border Adjustment Mechanism**
(Regulation (EU) 2023/956). It does four things:

1. **Regulation Q&A** — chat with an LLM grounded in CBAM context.
2. **Supplier-document extraction** — paste a supplier emissions report; the LLM
   returns structured CBAM fields (CN code, quantity, embedded direct/indirect
   emissions, installation, carbon price paid, …).
3. **Goods registry** — keeps the imported goods for the current quarter in an
   in-memory store.
4. **Quarterly report XML** — generates a CBAM Transitional Registry quarterly
   report in XML, ready to download.

> **Status:** MVP. The XML structure mirrors the spirit and field names of the
> official CBAM-QUARTERLY-REPORT format but is **not** byte-perfect against the
> EU XSD. Default emission values in `backend/reference.py` are illustrative
> placeholders. Replace both before submitting anything to the real Registry.

Lives in its own folder (`cbam/`), independent of the rest of this repo.

## Stack

- **Backend:** FastAPI + Pydantic (Python 3.10+)
- **AI:** OpenAI Chat Completions (`gpt-4o-mini` by default, override via
  `OPENAI_MODEL`)
- **Frontend:** vanilla HTML / CSS / JS, served by the FastAPI app
- **Storage:** in-memory dict (swap for a DB later)

## Run it

```bash
cd cbam
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # then put your OPENAI_API_KEY in .env
./run.sh
```

Open <http://localhost:8080>.

## Tests

```bash
cd cbam
PYTHONPATH=. pytest -q
```

Tests are offline (no OpenAI calls).

## API

| Method | Path                | Purpose                                     |
| ------ | ------------------- | ------------------------------------------- |
| GET    | `/api/health`       | liveness + whether `OPENAI_API_KEY` is set  |
| GET    | `/api/reference`    | sectors, CN codes, default emissions, ctx   |
| POST   | `/api/qa`           | regulation Q&A                              |
| POST   | `/api/extract`      | supplier document → structured fields       |
| GET    | `/api/goods`        | list registered goods                       |
| POST   | `/api/goods`        | add a good                                  |
| DELETE | `/api/goods/{id}`   | delete a good                               |
| POST   | `/api/report`       | build and download the quarterly XML        |

## Layout

```
cbam/
├── backend/
│   ├── main.py        FastAPI app, routes, in-memory store
│   ├── models.py      Pydantic schemas
│   ├── reference.py   sectors, CN codes, default emissions, regulation context
│   ├── ai.py          OpenAI calls (Q&A + extraction)
│   └── report.py      quarterly-report XML builder
├── frontend/          single-page UI (no build step)
├── sample_data/       sample supplier reports + sample report input
├── tests/             pytest, offline
├── requirements.txt
├── .env.example
└── run.sh
```

## Known limitations

- XML schema is illustrative, not the official XSD.
- Default emission values are placeholders.
- No authentication.
- In-memory storage — restarting the server wipes the goods registry.
- Extraction handles plain text only (PDF parsing not wired in yet).
