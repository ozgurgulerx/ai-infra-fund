-- Phase 11 macro time-series snapshots.
-- Vintage-aware: a revised observation creates a new row, never overwrites.
-- See AGENTS.md lookahead-bias rule and plan: free public data integration.

CREATE TABLE IF NOT EXISTS signals.macro_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    series_id TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES evidence.source_registry(source_id) ON DELETE CASCADE,
    as_of TIMESTAMPTZ NOT NULL,
    value NUMERIC,
    unit TEXT NOT NULL,
    vintage_id TEXT NOT NULL,
    content_hash TEXT NOT NULL UNIQUE,
    ingested_at TIMESTAMPTZ NOT NULL,
    UNIQUE (series_id, as_of, vintage_id)
);

CREATE INDEX IF NOT EXISTS macro_snapshots_series_asof_idx
    ON signals.macro_snapshots (series_id, as_of DESC);
