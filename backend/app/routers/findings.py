"""Finding endpoints (review queue + detail + re-analysis)."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Finding
from ..routers.records import _finding_out
from ..schemas import FindingDetailOut, FindingOut, ReviewOut, SourceRecordOut
from ..services.ai_engine import extract_evidence
from ..services.audit import ACTOR_SYSTEM, log_event

router = APIRouter(prefix="/findings", tags=["findings"])


def _latest_status(f: Finding) -> str:
    if not f.reviews:
        return "PENDING"
    return max(f.reviews, key=lambda r: (r.reviewed_at, r.id)).status.value


@router.get("", response_model=list[FindingOut])
def list_findings(
    status: str | None = Query(default=None, description="PENDING | APPROVED | REJECTED | MODIFIED"),
    category: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = (
        db.query(Finding)
        .options(selectinload(Finding.reviews), selectinload(Finding.source_record))
        .order_by(desc(Finding.created_at))
    )
    if category:
        q = q.filter(Finding.category == category)
    findings = q.limit(limit * 3).all()  # over-fetch: status filter is computed
    out = [_finding_out(f, _latest_status(f)) for f in findings]
    if status:
        out = [f for f in out if f.review_status == status.upper()]
    return out[:limit]


@router.get("/{finding_id}", response_model=FindingDetailOut)
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    f = (
        db.query(Finding)
        .options(selectinload(Finding.reviews), selectinload(Finding.source_record))
        .filter(Finding.id == finding_id)
        .first()
    )
    if not f:
        raise HTTPException(status_code=404, detail="Finding not found")
    detail = FindingDetailOut(
        **_finding_out(f, _latest_status(f)).model_dump(),
        source_record=SourceRecordOut.model_validate(f.source_record) if f.source_record else None,
        reviews=[ReviewOut.model_validate(r) for r in sorted(f.reviews, key=lambda r: r.reviewed_at)],
    )
    return detail


@router.post("/{finding_id}/reanalyze", response_model=FindingOut)
def reanalyze_finding(finding_id: str, db: Session = Depends(get_db)):
    """Re-run the AI engine on the finding's source text (creates new version in place)."""
    f = db.query(Finding).filter(Finding.id == finding_id).first()
    if not f or not f.source_record:
        raise HTTPException(status_code=404, detail="Finding not found")
    extraction, engine_version = extract_evidence(f.source_record.raw_text)
    imdrf = extraction.imdrf_coding
    f.category = extraction.category
    f.exact_quote = extraction.exact_quote
    f.plain_language_rationale = extraction.relevance_rationale
    f.confidence_score = extraction.confidence_score
    f.imdrf_annex_a = imdrf.annex_a_code if imdrf else None
    f.imdrf_annex_a_label = imdrf.annex_a_label if imdrf else None
    f.imdrf_annex_e = imdrf.annex_e_code if imdrf else None
    f.imdrf_annex_e_label = imdrf.annex_e_label if imdrf else None
    f.ai_model_version = engine_version
    db.flush()
    log_event(db, entity_type="finding", entity_id=f.id, action="AI_REANALYZE",
              actor=ACTOR_SYSTEM,
              payload={"category": f.category, "confidence": f.confidence_score, "engine": engine_version})
    db.commit()
    db.refresh(f)
    return _finding_out(f, _latest_status(f))
