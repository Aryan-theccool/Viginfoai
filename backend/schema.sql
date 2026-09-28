-- ═══════════════════════════════════════════════════════════════════
-- VigInfo AI — PostgreSQL schema (production reference)
-- System of record for clinical evidence & post-market surveillance (EU MDR)
--
-- The FastAPI app auto-creates an equivalent schema via SQLAlchemy (SQLite
-- by default for local dev). Use this file to provision PostgreSQL and to
-- demonstrate auditability to a Notified Body / 21 CFR Part 11 reviewer.
-- ═══════════════════════════════════════════════════════════════════

-- ── Source Data Table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_type VARCHAR(50) NOT NULL,      -- 'PubMed' | 'FDA MAUDE' | 'Uploaded_PDF' | 'Manual'
    external_id VARCHAR(100) NOT NULL,
    title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    record_metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ── AI Identified Findings ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_record_id UUID REFERENCES source_records(id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,         -- 'Clinical Performance' | 'Safety Signal' | 'Risk' | 'Irrelevant'
    exact_quote TEXT NOT NULL,
    plain_language_rationale TEXT NOT NULL,
    confidence_score NUMERIC(3, 2),
    imdrf_annex_a VARCHAR(20),
    imdrf_annex_a_label TEXT,
    imdrf_annex_e VARCHAR(20),
    imdrf_annex_e_label TEXT,
    ai_model_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ── Human Review Workflow States ───────────────────────────────
DO $$ BEGIN
    CREATE TYPE review_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'MODIFIED');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS human_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    finding_id UUID REFERENCES findings(id) ON DELETE CASCADE,
    reviewer_email VARCHAR(255) NOT NULL,
    status review_status NOT NULL,
    override_category VARCHAR(50),
    reviewer_notes TEXT,
    reviewed_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- ── Immutable Audit Trail (append-only by convention + trigger) ─
CREATE TABLE IF NOT EXISTS audit_trail (
    audit_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,      -- 'record' | 'finding' | 'review'
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,           -- 'CREATE' | 'AI_EXTRACT' | 'REVIEW_SUBMIT' | 'OVERRIDE' ...
    actor VARCHAR(255) NOT NULL,           -- user email or 'system-ai'
    payload JSONB NOT NULL,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Enforce append-only: forbid UPDATE / DELETE on the audit ledger.
CREATE OR REPLACE FUNCTION forbid_audit_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_trail is append-only (EU MDR / 21 CFR Part 11)';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_audit_no_update ON audit_trail;
CREATE TRIGGER trg_audit_no_update
    BEFORE UPDATE OR DELETE ON audit_trail
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();

-- ── Indexes for regulatory querying ────────────────────────────
CREATE INDEX IF NOT EXISTS idx_records_source ON source_records(source_type, external_id);
CREATE INDEX IF NOT EXISTS idx_findings_source ON findings(source_record_id);
CREATE INDEX IF NOT EXISTS idx_findings_category ON findings(category);
CREATE INDEX IF NOT EXISTS idx_reviews_finding ON human_reviews(finding_id);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_trail(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_trail(timestamp DESC);
