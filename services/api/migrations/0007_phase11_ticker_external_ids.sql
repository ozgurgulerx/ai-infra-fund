-- Phase 11 ticker → external identifier mapping.
-- Generic table for SEC CIK, FIGI, ISIN, LEI, etc., one row per (ticker, system).

CREATE TABLE IF NOT EXISTS evidence.ticker_external_ids (
    ticker TEXT NOT NULL REFERENCES core.watched_equities(ticker) ON DELETE CASCADE,
    system TEXT NOT NULL,
    external_id TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, system)
);

CREATE INDEX IF NOT EXISTS ticker_external_ids_system_external_idx
    ON evidence.ticker_external_ids (system, external_id);
