"""Source-record endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Finding, HumanReview, SourceRecord
from ..schemas import FindingOut, RecordDetailOut, SourceRecordOut

router = APIRouter(prefix="/records", tags=["records"])


def _finding_out(f: Finding, latest_status: str = "PENDING") -> FindingOut:
    return FindingOut(
        id=f.id, source_record_id=f.source_record_id, category=f.category,
        exact_quote=f.exact_quote, plain_language_rationale=f.plain_language_rationale,
        confidence_score=f.confidence_score, imdrf_annex_a=f.imdrf_annex_a,
        imdrf_annex_a_label=f.imdrf_annex_a_label, imdrf_annex_e=f.imdrf_annex_e,
        imdrf_annex_e_label=f.imdrf_annex_e_label, ai_model_version=f.ai_model_version,
        created_at=f.created_at, review_status=latest_status,
        source_title=f.source_record.title if f.source_record else None,
        source_type=f.source_record.source_type if f.source_record else None,
    )


@router.get("", response_model=list[SourceRecordOut])
def list_records(
    source_type: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(SourceRecord).order_by(desc(SourceRecord.created_at))
    if source_type:
        q = q.filter(SourceRecord.source_type == source_type)
    if search:
        like = f"%{search}%"
        q = q.filter((SourceRecord.title.ilike(like)) | (SourceRecord.raw_text.ilike(like)))
    return q.limit(limit).all()


@router.get("/{record_id}", response_model=RecordDetailOut)
def get_record(record_id: str, db: Session = Depends(get_db)):
    record = (
        db.query(SourceRecord)
        .options(selectinload(SourceRecord.findings).selectinload(Finding.reviews))
        .filter(SourceRecord.id == record_id)
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    out = RecordDetailOut.model_validate(record)
    findings: list[FindingOut] = []
    for f in record.findings:
        latest = max(f.reviews, key=lambda r: r.reviewed_at) if f.reviews else None
        findings.append(_finding_out(f, latest.status.value if latest else "PENDING"))
    out.findings = findings
    return out
