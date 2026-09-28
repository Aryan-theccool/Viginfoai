"""Human-in-the-loop review endpoints (decision-support, never autonomous)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Finding, HumanReview, ReviewStatus
from ..schemas import ReviewCreate, ReviewOut
from ..services.audit import log_event

router = APIRouter(prefix="/reviews", tags=["reviews"])

ALLOWED = {"APPROVED", "REJECTED", "MODIFIED"}


@router.post("", response_model=ReviewOut, status_code=201)
def submit_review(payload: ReviewCreate, db: Session = Depends(get_db)):
    status = payload.status.upper()
    if status not in ALLOWED:
        raise HTTPException(status_code=422, detail=f"status must be one of {sorted(ALLOWED)}")
    finding = db.query(Finding).filter(Finding.id == payload.finding_id).first()
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    if status == "MODIFIED" and not payload.override_category:
        raise HTTPException(status_code=422, detail="MODIFIED reviews require override_category")

    review = HumanReview(
        finding_id=finding.id,
        reviewer_email=payload.reviewer_email,
        status=ReviewStatus(status),
        override_category=payload.override_category,
        reviewer_notes=payload.reviewer_notes,
    )
    db.add(review)
    db.flush()
    action = "REVIEW_OVERRIDE" if status == "MODIFIED" else "REVIEW_SUBMIT"
    log_event(
        db, entity_type="review", entity_id=review.id, action=action,
        actor=payload.reviewer_email,
        payload={"finding_id": finding.id, "status": status,
                 "ai_category": finding.category,
                 "override_category": payload.override_category,
                 "notes": payload.reviewer_notes},
    )
    db.commit()
    db.refresh(review)
    return ReviewOut.model_validate(review)


@router.get("/finding/{finding_id}", response_model=list[ReviewOut])
def list_reviews_for_finding(finding_id: str, db: Session = Depends(get_db)):
    return db.query(HumanReview).filter(HumanReview.finding_id == finding_id).order_by(HumanReview.reviewed_at).all()
