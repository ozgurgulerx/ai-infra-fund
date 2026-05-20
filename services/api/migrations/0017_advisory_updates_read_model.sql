CREATE SCHEMA IF NOT EXISTS analyst;

CREATE TABLE IF NOT EXISTS analyst.advisory_updates (
    update_id TEXT PRIMARY KEY CHECK (update_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    company TEXT,
    previous_advisory_id TEXT,
    new_advisory_id TEXT,
    previous_label TEXT,
    current_label TEXT NOT NULL CHECK (current_label <> ''),
    what_changed TEXT NOT NULL CHECK (what_changed <> ''),
    update_type TEXT NOT NULL DEFAULT 'advisory_delta' CHECK (update_type <> ''),
    thesis_change_direction TEXT NOT NULL DEFAULT 'review_needed' CHECK (thesis_change_direction <> ''),
    risk_change_direction TEXT NOT NULL DEFAULT 'review_needed' CHECK (risk_change_direction <> ''),
    valuation_change_direction TEXT NOT NULL DEFAULT 'review_needed' CHECK (valuation_change_direction <> ''),
    confidence_change TEXT NOT NULL DEFAULT 'review_needed' CHECK (confidence_change <> ''),
    time_horizon TEXT,
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    model_run_ids TEXT[] NOT NULL DEFAULT '{}',
    deterministic_check_ids TEXT[] NOT NULL DEFAULT '{}',
    advisory_label TEXT NOT NULL DEFAULT 'advisory_only' CHECK (advisory_label = 'advisory_only'),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS advisory_updates_ticker_idx ON analyst.advisory_updates (ticker);
CREATE INDEX IF NOT EXISTS advisory_updates_created_at_idx ON analyst.advisory_updates (created_at DESC);
CREATE INDEX IF NOT EXISTS advisory_updates_evidence_ids_idx ON analyst.advisory_updates USING gin (evidence_ids);
CREATE INDEX IF NOT EXISTS advisory_updates_model_run_ids_idx ON analyst.advisory_updates USING gin (model_run_ids);
