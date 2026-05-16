CREATE SCHEMA IF NOT EXISTS analyst;

CREATE TABLE IF NOT EXISTS analyst.risk_regime_updates (
    regime_id TEXT PRIMARY KEY CHECK (regime_id <> ''),
    risk_type TEXT NOT NULL CHECK (risk_type <> ''),
    status TEXT NOT NULL CHECK (status <> ''),
    severity TEXT NOT NULL DEFAULT 'medium' CHECK (severity <> ''),
    confidence TEXT NOT NULL DEFAULT 'medium' CHECK (confidence <> ''),
    linked_event_ids TEXT[] NOT NULL DEFAULT '{}',
    affected_segments TEXT[] NOT NULL DEFAULT '{}',
    affected_tickers TEXT[] NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    summary TEXT NOT NULL CHECK (summary <> ''),
    portfolio_monitoring_note TEXT NOT NULL CHECK (portfolio_monitoring_note <> ''),
    relief_condition TEXT,
    invalidation_condition TEXT,
    as_of TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS risk_regime_updates_event_ids_idx ON analyst.risk_regime_updates USING gin (linked_event_ids);
CREATE INDEX IF NOT EXISTS risk_regime_updates_tickers_idx ON analyst.risk_regime_updates USING gin (affected_tickers);
CREATE INDEX IF NOT EXISTS risk_regime_updates_evidence_ids_idx ON analyst.risk_regime_updates USING gin (evidence_ids);
CREATE INDEX IF NOT EXISTS risk_regime_updates_available_at_idx ON analyst.risk_regime_updates (available_at DESC);

CREATE TABLE IF NOT EXISTS analyst.trade_plans (
    trade_plan_id TEXT PRIMARY KEY CHECK (trade_plan_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    company TEXT NOT NULL CHECK (company <> ''),
    status TEXT NOT NULL CHECK (status <> ''),
    advisory_action TEXT NOT NULL CHECK (advisory_action IN ('watch', 'accumulate', 'hold', 'trim', 'avoid', 'review', 'exit-candidate')),
    linked_event_ids TEXT[] NOT NULL DEFAULT '{}',
    linked_signal_bundle_id TEXT,
    linked_recommendation_artifact_id TEXT,
    entry_exit_levels_id TEXT,
    price_target_scenario_id TEXT,
    target_weights_id TEXT,
    deterministic_check_ids TEXT[] NOT NULL DEFAULT '{}',
    readiness TEXT NOT NULL DEFAULT 'review_needed' CHECK (readiness <> ''),
    blocking_reasons TEXT[] NOT NULL DEFAULT '{}',
    manual_journal_only BOOLEAN NOT NULL DEFAULT true CHECK (manual_journal_only = true),
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    linked_advisory_id TEXT,
    last_reviewed_at TIMESTAMPTZ,
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS trade_plans_ticker_idx ON analyst.trade_plans (ticker);
CREATE INDEX IF NOT EXISTS trade_plans_event_ids_idx ON analyst.trade_plans USING gin (linked_event_ids);
CREATE INDEX IF NOT EXISTS trade_plans_evidence_ids_idx ON analyst.trade_plans USING gin (evidence_ids);
CREATE INDEX IF NOT EXISTS trade_plans_status_idx ON analyst.trade_plans (status);

CREATE TABLE IF NOT EXISTS analyst.portfolio_exposure_snapshots (
    snapshot_id TEXT PRIMARY KEY CHECK (snapshot_id <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    currency TEXT NOT NULL CHECK (currency <> ''),
    source TEXT NOT NULL CHECK (source <> ''),
    advisory_label TEXT NOT NULL DEFAULT 'advisory_only' CHECK (advisory_label = 'advisory_only'),
    total_market_value TEXT NOT NULL CHECK (total_market_value <> ''),
    cash_placeholder TEXT NOT NULL CHECK (cash_placeholder <> ''),
    gross_equity_exposure TEXT NOT NULL CHECK (gross_equity_exposure <> ''),
    position_count INTEGER NOT NULL CHECK (position_count >= 0),
    positions_json JSONB NOT NULL DEFAULT '[]',
    correlation_exposure_ids TEXT[] NOT NULL DEFAULT '{}',
    pnl_summary_id TEXT,
    target_weights_id TEXT,
    concentration_flags TEXT[] NOT NULL DEFAULT '{}',
    stale_price_flags TEXT[] NOT NULL DEFAULT '{}',
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS portfolio_exposure_snapshots_as_of_idx ON analyst.portfolio_exposure_snapshots (as_of DESC);
CREATE INDEX IF NOT EXISTS portfolio_exposure_snapshots_correlation_idx ON analyst.portfolio_exposure_snapshots USING gin (correlation_exposure_ids);

CREATE TABLE IF NOT EXISTS analyst.llm_analyst_notes (
    note_id TEXT PRIMARY KEY CHECK (note_id <> ''),
    model_run_id TEXT NOT NULL CHECK (model_run_id <> ''),
    scope TEXT NOT NULL CHECK (scope <> ''),
    allowed_role TEXT NOT NULL CHECK (allowed_role <> ''),
    reviewed_object_ids TEXT[] NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL DEFAULT '{}',
    note TEXT NOT NULL CHECK (note <> ''),
    deterministic_fields_not_modified TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    review_status TEXT NOT NULL DEFAULT 'pending_review' CHECK (review_status <> ''),
    payload_json JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS llm_analyst_notes_model_run_idx ON analyst.llm_analyst_notes (model_run_id);
CREATE INDEX IF NOT EXISTS llm_analyst_notes_reviewed_object_ids_idx ON analyst.llm_analyst_notes USING gin (reviewed_object_ids);
CREATE INDEX IF NOT EXISTS llm_analyst_notes_evidence_ids_idx ON analyst.llm_analyst_notes USING gin (evidence_ids);
