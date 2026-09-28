"""Immutable audit-trail endpoints (read-only — the ledger is append-only)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditEntry
from ..schemas import AuditOut

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=list[AuditOut])
def list_audit(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    finding_id: str | None = Query(default=None, description="All events for a finding + its reviews + its record"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    q = db.query(AuditEntry).order_by(desc(AuditEntry.timestamp), desc(AuditEntry.audit_id))
    if finding_id:
        from ..models import Finding, HumanReview  # local import: avoids circulars

        f = db.query(Finding).filter(Finding.id == finding_id).first()
        review_ids = [r.id for r in db.query(HumanReview).filter(HumanReview.finding_id == finding_id).all()] if f else []
        ids = [finding_id] + review_ids + ([f.source_record_id] if f else [])
        q = q.filter(AuditEntry.entity_id.in_(ids))
    else:
        if entity_type:
            q = q.filter(AuditEntry.entity_type == entity_type)
        if entity_id:
            q = q.filter(AuditEntry.entity_id == entity_id)
    return q.limit(limit).all()
