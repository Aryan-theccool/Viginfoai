"""Pydantic request/response schemas for the REST API."""
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field

# ── Ingestion ────────────────────────────────────────────────────


class PubMedIngestRequest(BaseModel):
    query: str = Field(examples=['("infusion pump") AND ("adverse event" OR "safety")'])
    max_results: int = Field(default=10, ge=1, le=50)


class MaudeIngestRequest(BaseModel):
    device_name: str = Field(examples=["infusion pump"])
    limit: int = Field(default=10, ge=1, le=50)


class ManualIngestRequest(BaseModel):
    title: str
    text: str = Field(min_length=20)
    source_type: str = Field(default="Manual", examples=["Uploaded_PDF", "Manual"])
    external_id: Optional[str] = None


class IngestResult(BaseModel):
    records_created: int
    findings_created: int
    record_ids: list[str]
    finding_ids: list[str]
    engine: str


# ── Records & findings ───────────────────────────────────────────


class SourceRecordOut(BaseModel):
    id: str
    source_type: str
    external_id: str
    title: str
    raw_text: str
    record_metadata: dict[str, Any] = {}
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ReviewOut(BaseModel):
    id: str
    finding_id: str
    reviewer_email: str
    status: str
    override_category: Optional[str] = None
    reviewer_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FindingOut(BaseModel):
    id: str
    source_record_id: str
    category: str
    exact_quote: str
    plain_language_rationale: str
    confidence_score: Optional[float] = None
    imdrf_annex_a: Optional[str] = None
    imdrf_annex_a_label: Optional[str] = None
    imdrf_annex_e: Optional[str] = None
    imdrf_annex_e_label: Optional[str] = None
    ai_model_version: str
    created_at: Optional[datetime] = None
    review_status: str = "PENDING"
    source_title: Optional[str] = None
    source_type: Optional[str] = None

    model_config = {"from_attributes": True}


class RecordDetailOut(SourceRecordOut):
    findings: list[FindingOut] = []


class FindingDetailOut(FindingOut):
    source_record: Optional[SourceRecordOut] = None
    reviews: list[ReviewOut] = []


# ── Reviews ──────────────────────────────────────────────────────


class ReviewCreate(BaseModel):
    finding_id: str
    reviewer_email: str
    status: str = Field(examples=["APPROVED", "REJECTED", "MODIFIED"])
    override_category: Optional[str] = None
    reviewer_notes: Optional[str] = None


# ── Audit ────────────────────────────────────────────────────────


class AuditOut(BaseModel):
    audit_id: int
    entity_type: str
    entity_id: str
    action: str
    actor: str
    payload: dict[str, Any] = {}
    timestamp: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ── Stats ────────────────────────────────────────────────────────


class StatsOut(BaseModel):
    records: int
    findings: int
    pending: int
    approved: int
    rejected: int
    modified: int
    safety_signals: int
    by_category: dict[str, int]
    engine: str
