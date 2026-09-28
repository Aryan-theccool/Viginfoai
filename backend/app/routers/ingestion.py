"""Ingestion endpoints: PubMed, FDA MAUDE, manual text."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import IngestResult, ManualIngestRequest, MaudeIngestRequest, PubMedIngestRequest
from ..services.ai_engine import current_engine_version
from ..services.maude import MaudeIngestor
from ..services.pipeline import store_record_with_analysis
from ..services.pubmed import PubMedIngestor

router = APIRouter(prefix="/ingest", tags=["ingestion"])


@router.post("/pubmed", response_model=IngestResult)
def ingest_pubmed(payload: PubMedIngestRequest, db: Session = Depends(get_db)):
    try:
        articles = PubMedIngestor().ingest(payload.query, max_results=payload.max_results)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"PubMed request failed: {exc}") from exc
    return _store_items(db, articles)


@router.post("/maude", response_model=IngestResult)
def ingest_maude(payload: MaudeIngestRequest, db: Session = Depends(get_db)):
    try:
        incidents = MaudeIngestor().fetch_incidents(payload.device_name, limit=payload.limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"openFDA request failed: {exc}") from exc
    return _store_items(db, incidents)


@router.post("/manual", response_model=IngestResult)
def ingest_manual(payload: ManualIngestRequest, db: Session = Depends(get_db)):
    record, finding = store_record_with_analysis(
        db,
        source_type=payload.source_type,
        external_id=payload.external_id or "manual-entry",
        title=payload.title,
        text=payload.text,
        metadata={"ingested_via": "manual"},
    )
    return IngestResult(
        records_created=1, findings_created=1,
        record_ids=[record.id], finding_ids=[finding.id],
        engine=current_engine_version(),
    )


def _store_items(db: Session, items: list[dict]) -> IngestResult:
    record_ids: list[str] = []
    finding_ids: list[str] = []
    for item in items:
        meta = {k: v for k, v in item.items() if k not in ("source", "source_id", "title", "text")}
        record, finding = store_record_with_analysis(
            db,
            source_type=item.get("source", "Unknown"),
            external_id=str(item.get("source_id", "unknown")),
            title=item.get("title", "Untitled"),
            text=item.get("text", ""),
            metadata=meta,
        )
        record_ids.append(record.id)
        finding_ids.append(finding.id)
    return IngestResult(
        records_created=len(record_ids), findings_created=len(finding_ids),
        record_ids=record_ids, finding_ids=finding_ids,
        engine=current_engine_version(),
    )
