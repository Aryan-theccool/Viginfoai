"""Dashboard statistics."""
from collections import Counter

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, selectinload

from ..database import get_db
from ..models import Finding, SourceRecord
from ..schemas import StatsOut
from ..services.ai_engine import current_engine_version

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)):
    records = db.query(SourceRecord).count()
    findings = db.query(Finding).options(selectinload(Finding.reviews)).all()
    statuses: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    for f in findings:
        categories[f.category] += 1
        statuses[max(f.reviews, key=lambda r: (r.reviewed_at, r.id)).status.value if f.reviews else "PENDING"] += 1
    return StatsOut(
        records=records,
        findings=len(findings),
        pending=statuses.get("PENDING", 0),
        approved=statuses.get("APPROVED", 0),
        rejected=statuses.get("REJECTED", 0),
        modified=statuses.get("MODIFIED", 0),
        safety_signals=categories.get("Safety Signal", 0),
        by_category=dict(categories),
        engine=current_engine_version(),
    )
