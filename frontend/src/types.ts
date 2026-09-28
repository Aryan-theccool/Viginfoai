export interface SourceRecord {
  id: string;
  source_type: string;
  external_id: string;
  title: string;
  raw_text: string;
  record_metadata: Record<string, unknown>;
  created_at?: string;
}

export interface Finding {
  id: string;
  source_record_id: string;
  category: string;
  exact_quote: string;
  plain_language_rationale: string;
  confidence_score?: number | null;
  imdrf_annex_a?: string | null;
  imdrf_annex_a_label?: string | null;
  imdrf_annex_e?: string | null;
  imdrf_annex_e_label?: string | null;
  ai_model_version: string;
  created_at?: string;
  review_status: string;
  source_title?: string | null;
  source_type?: string | null;
}

export interface Review {
  id: string;
  finding_id: string;
  reviewer_email: string;
  status: string;
  override_category?: string | null;
  reviewer_notes?: string | null;
  reviewed_at?: string;
}

export interface FindingDetail extends Finding {
  source_record?: SourceRecord | null;
  reviews: Review[];
}

export interface AuditEntry {
  audit_id: number;
  entity_type: string;
  entity_id: string;
  action: string;
  actor: string;
  payload: Record<string, unknown>;
  timestamp?: string;
}

export interface Stats {
  records: number;
  findings: number;
  pending: number;
  approved: number;
  rejected: number;
  modified: number;
  safety_signals: number;
  by_category: Record<string, number>;
  engine: string;
}
