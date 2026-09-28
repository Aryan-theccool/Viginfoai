# VigInfo AI — System of Record for MDR Evidence & Vigilance

An MVP of a **medical-device safety intelligence platform** under **EU MDR 2017/745**:
ingest literature (PubMed) and adverse events (FDA MAUDE), extract **explainable,
IMDRF-coded findings** with verbatim source quotes, route them through **human-in-the-loop
review**, and persist everything to an **immutable audit trail**.

> **Never a black box.** Every AI claim carries its exact source quote, a plain-language
> rationale, a confidence score, and IMDRF Annex A/E coding suggestions — approved or
> overridden by a human reviewer. Decision-support only (EU AI Act non-high-risk).

```
 Ingestion (PubMed / MAUDE / manual)
        │  AI Processing Engine (explainable extraction + IMDRF coding)
        ▼  Human-in-the-Loop Review (approve / reject / override)
        │  Immutable Audit Trail (append-only ledger)
        ▼
 CER evidence (Art. 61, Annex XIV)   ·   PMS / PSUR signals (Art. 83–90)
```

## Quickstart (2 minutes, fully offline)

**Prerequisites:** Python 3.11+, Node 18+.

```bash
# 1. Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
# → API + OpenAPI docs at http://localhost:8000/docs
# → Demo data (infusion pump + glucose monitor) seeds automatically

# 2. Frontend (new terminal)
cd frontend
npm install
npm run dev
# → UI at http://localhost:5173
```

No API keys required: without `OPENAI_API_KEY`, the built-in **explainable heuristic
engine** (`viginfo-heuristic-v1`) performs deterministic, traceable extraction. Set
`OPENAI_API_KEY` in `backend/.env` (see `.env.example`) to upgrade to GPT-4o structured
outputs — with automatic fallback if the API is unreachable.

## Architecture

| Layer | Tech | Location |
|---|---|---|
| API | FastAPI, SQLAlchemy 2.0, Pydantic v2 | `backend/app/` |
| DB | SQLite (dev) / PostgreSQL + JSONB (prod, `schema.sql`) | `backend/app/models.py` |
| AI engine | OpenAI structured outputs **or** offline heuristic engine | `backend/app/services/ai_engine.py` |
| Ingestion | NCBI E-utilities (PubMed), openFDA (MAUDE) | `backend/app/services/` |
| UI | React 18 + TypeScript + Tailwind (split-view review) | `frontend/src/` |

### API surface

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/ingest/pubmed` | Search + fetch PubMed articles → auto-analyzed |
| POST | `/api/ingest/maude` | Fetch MAUDE adverse events → auto-analyzed |
| POST | `/api/ingest/manual` | Analyze pasted text (PDFs, complaints) |
| GET | `/api/findings?status=PENDING` | Review queue |
| GET | `/api/findings/{id}` | Finding + source + review history |
| POST | `/api/findings/{id}/reanalyze` | Re-run AI extraction |
| POST | `/api/reviews` | Approve / Reject / Override (audited) |
| GET | `/api/audit?finding_id=…` | Finding-scoped audit timeline |
| GET | `/api/stats` | Dashboard counts |

### Data model

- `source_records` — raw ingested documents (PubMed / MAUDE / manual + JSONB metadata)
- `findings` — AI extractions (category, verbatim quote, rationale, confidence, IMDRF A/E)
- `human_reviews` — PENDING → APPROVED / REJECTED / MODIFIED (+ override category, notes)
- `audit_trail` — append-only ledger (`CREATE`, `AI_EXTRACT`, `REVIEW_SUBMIT`, `REVIEW_OVERRIDE`);
  PostgreSQL deployments enforce immutability with a trigger (see `schema.sql`)

## Regulatory mapping

| Requirement | Implementation |
|---|---|
| EU MDR Art. 61 + Annex XIV (CER) | Clinical Performance findings with MEDDEV 2.7/1-style appraisal trail |
| EU MDR Art. 83–90 (PMS/PSUR/vigilance) | Safety Signal findings from MAUDE + literature, trendable by IMDRF code |
| IMDRF AE terminology | Annex A (device problem) + Annex E (health effect) suggestions on every signal |
| 21 CFR Part 11 / Annex 11 | Timestamped, actor-stamped, append-only audit ledger |
| EU AI Act | Human-in-the-loop decision support → non-high-risk positioning |

## Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest tests/ -q
# 9 tests: engine classification + IMDRF coding + full review/audit workflow
```

## Production notes

- Point `DATABASE_URL` at PostgreSQL and apply `backend/schema.sql` (includes the
  append-only audit trigger + regulatory indexes).
- `docker-compose up` provisions API + Postgres.
- Add authentication (SSO/OIDC) in front of `/api/reviews` before pilot use; reviewer
  email is currently self-asserted for demo purposes.

## Demo

See [`docs/demo_script.md`](docs/demo_script.md) for the 90-second Loom walkthrough:
live MAUDE fetch → highlighted-quote review → approve → audit trail.
