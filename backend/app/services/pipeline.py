"""Orchestration: source record → AI extraction → finding → audit entries."""
from sqlalchemy.orm import Session

from ..models import Finding, SourceRecord
from .ai_engine import extract_evidence
from .audit import ACTOR_SYSTEM, log_event


def store_record_with_analysis(
    db: Session,
    *,
    source_type: str,
    external_id: str,
    title: str,
    text: str,
    metadata: dict | None = None,
) -> tuple[SourceRecord, Finding]:
    record = SourceRecord(
        source_type=source_type,
        external_id=external_id,
        title=title,
        raw_text=text,
        record_metadata=metadata or {},
    )
    db.add(record)
    db.flush()

    extraction, engine_version = extract_evidence(text)
    imdrf = extraction.imdrf_coding

    finding = Finding(
        source_record_id=record.id,
        category=extraction.category,
        exact_quote=extraction.exact_quote,
        plain_language_rationale=extraction.relevance_rationale,
        confidence_score=extraction.confidence_score,
        imdrf_annex_a=imdrf.annex_a_code if imdrf else None,
        imdrf_annex_a_label=imdrf.annex_a_label if imdrf else None,
        imdrf_annex_e=imdrf.annex_e_code if imdrf else None,
        imdrf_annex_e_label=imdrf.annex_e_label if imdrf else None,
        ai_model_version=engine_version,
    )
    db.add(finding)
    db.flush()

    log_event(db, entity_type="record", entity_id=record.id, action="CREATE",
              actor=ACTOR_SYSTEM, payload={"source_type": source_type, "external_id": external_id, "title": title})
    log_event(db, entity_type="finding", entity_id=finding.id, action="AI_EXTRACT",
              actor=ACTOR_SYSTEM,
              payload={"category": finding.category, "confidence": finding.confidence_score,
                       "engine": engine_version, "indicators": extraction.matched_indicators})
    db.commit()
    db.refresh(record)
    db.refresh(finding)
    return record, finding
