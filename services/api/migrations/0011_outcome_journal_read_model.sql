CREATE SCHEMA IF NOT EXISTS analyst;

CREATE TABLE IF NOT EXISTS analyst.outcome_journal_entries (
    outcome_id TEXT PRIMARY KEY CHECK (outcome_id <> ''),
    manual_journal_entry_id UUID NOT NULL REFERENCES core.trade_entries(trade_id),
    advisory_id TEXT NOT NULL REFERENCES analyst.trading_advisories(advisory_id) CHECK (advisory_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    market_event_ids TEXT[] NOT NULL DEFAULT '{}' CHECK (cardinality(market_event_ids) > 0),
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    review_status TEXT NOT NULL CHECK (review_status <> ''),
    outcome_label TEXT NOT NULL CHECK (outcome_label <> ''),
    invalidation_flags TEXT[] NOT NULL DEFAULT '{}',
    risk_flags TEXT[] NOT NULL DEFAULT '{}',
    gross_pnl_amount NUMERIC,
    net_pnl_amount NUMERIC,
    pnl_percent NUMERIC,
    benchmark_pnl_percent NUMERIC,
    excess_pnl_percent NUMERIC,
    pnl_attribution_method TEXT NOT NULL CHECK (pnl_attribution_method <> ''),
    pnl_attribution_note TEXT,
    reviewed_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    advisory_label TEXT NOT NULL DEFAULT 'advisory_only' CHECK (advisory_label = 'advisory_only'),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS outcome_journal_entries_available_at_idx ON analyst.outcome_journal_entries (available_at DESC);
CREATE INDEX IF NOT EXISTS outcome_journal_entries_advisory_id_idx ON analyst.outcome_journal_entries (advisory_id);
CREATE INDEX IF NOT EXISTS outcome_journal_entries_manual_journal_entry_id_idx ON analyst.outcome_journal_entries (manual_journal_entry_id);
CREATE INDEX IF NOT EXISTS outcome_journal_entries_ticker_idx ON analyst.outcome_journal_entries (ticker);
CREATE INDEX IF NOT EXISTS outcome_journal_entries_market_event_ids_idx ON analyst.outcome_journal_entries USING gin (market_event_ids);
CREATE INDEX IF NOT EXISTS outcome_journal_entries_evidence_ids_idx ON analyst.outcome_journal_entries USING gin (evidence_ids);
