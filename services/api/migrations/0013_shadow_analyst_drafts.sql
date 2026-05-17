CREATE SCHEMA IF NOT EXISTS analyst;

CREATE TABLE IF NOT EXISTS analyst.shadow_analyst_drafts (
    draft_id TEXT PRIMARY KEY CHECK (draft_id <> ''),
    draft_type TEXT NOT NULL CHECK (draft_type <> ''),
    scope TEXT NOT NULL CHECK (scope IN ('daily', 'ticker')),
    ticker TEXT,
    source_model_run_id TEXT NOT NULL REFERENCES audit.model_runs(model_run_id),
    status TEXT NOT NULL CHECK (status IN ('review_required', 'rejected', 'fallback', 'accepted_for_publication', 'denied')),
    payload_json JSONB NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    validation_errors TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (status IN ('fallback', 'denied') OR cardinality(evidence_ids) > 0),
    CHECK (status <> 'rejected' OR cardinality(validation_errors) > 0)
);

CREATE INDEX IF NOT EXISTS shadow_analyst_drafts_model_run_idx ON analyst.shadow_analyst_drafts (source_model_run_id);
CREATE INDEX IF NOT EXISTS shadow_analyst_drafts_status_idx ON analyst.shadow_analyst_drafts (status);
CREATE INDEX IF NOT EXISTS shadow_analyst_drafts_created_at_idx ON analyst.shadow_analyst_drafts (created_at DESC);
CREATE INDEX IF NOT EXISTS shadow_analyst_drafts_evidence_ids_idx ON analyst.shadow_analyst_drafts USING gin (evidence_ids);
