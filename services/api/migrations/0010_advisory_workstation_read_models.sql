CREATE SCHEMA IF NOT EXISTS analyst;

CREATE TABLE IF NOT EXISTS analyst.source_signals (
    signal_id TEXT PRIMARY KEY CHECK (signal_id <> ''),
    source_type TEXT NOT NULL CHECK (source_type <> ''),
    signal_category TEXT NOT NULL CHECK (signal_category <> ''),
    title TEXT NOT NULL CHECK (title <> ''),
    observed_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    tickers TEXT[] NOT NULL DEFAULT '{}',
    themes TEXT[] NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    derived_market_event_ids TEXT[] NOT NULL DEFAULT '{}',
    confidence TEXT NOT NULL CHECK (confidence <> ''),
    review_status TEXT NOT NULL CHECK (review_status <> ''),
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS source_signals_available_at_idx ON analyst.source_signals (available_at DESC);
CREATE INDEX IF NOT EXISTS source_signals_tickers_idx ON analyst.source_signals USING gin (tickers);
CREATE INDEX IF NOT EXISTS source_signals_evidence_ids_idx ON analyst.source_signals USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS analyst.market_events (
    event_id TEXT PRIMARY KEY CHECK (event_id <> ''),
    event_type TEXT NOT NULL CHECK (event_type <> ''),
    source_signal_ids TEXT[] NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    tickers TEXT[] NOT NULL DEFAULT '{}',
    companies TEXT[] NOT NULL DEFAULT '{}',
    themes TEXT[] NOT NULL DEFAULT '{}',
    catalyst TEXT NOT NULL CHECK (catalyst <> ''),
    ai_relevance TEXT NOT NULL CHECK (ai_relevance <> ''),
    direction TEXT NOT NULL CHECK (direction <> ''),
    time_horizon TEXT NOT NULL CHECK (time_horizon <> ''),
    confidence TEXT NOT NULL CHECK (confidence <> ''),
    occurred_at TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    extracted_by_model_run_id TEXT,
    review_status TEXT NOT NULL CHECK (review_status <> ''),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS market_events_available_at_idx ON analyst.market_events (available_at DESC);
CREATE INDEX IF NOT EXISTS market_events_tickers_idx ON analyst.market_events USING gin (tickers);
CREATE INDEX IF NOT EXISTS market_events_evidence_ids_idx ON analyst.market_events USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS analyst.segment_impacts (
    segment_id TEXT PRIMARY KEY CHECK (segment_id <> ''),
    segment_name TEXT NOT NULL CHECK (segment_name <> ''),
    primary_tickers TEXT[] NOT NULL DEFAULT '{}',
    second_order_tickers TEXT[] NOT NULL DEFAULT '{}',
    linked_event_ids TEXT[] NOT NULL CHECK (cardinality(linked_event_ids) > 0),
    impact_direction TEXT NOT NULL CHECK (impact_direction <> ''),
    impact_summary TEXT NOT NULL CHECK (impact_summary <> ''),
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS segment_impacts_event_ids_idx ON analyst.segment_impacts USING gin (linked_event_ids);
CREATE INDEX IF NOT EXISTS segment_impacts_evidence_ids_idx ON analyst.segment_impacts USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS analyst.equity_impact_assessments (
    assessment_id TEXT PRIMARY KEY CHECK (assessment_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    company TEXT NOT NULL CHECK (company <> ''),
    linked_event_ids TEXT[] NOT NULL CHECK (cardinality(linked_event_ids) > 0),
    assessment TEXT NOT NULL CHECK (assessment <> ''),
    watch_items TEXT[] NOT NULL DEFAULT '{}',
    advisory_implication TEXT NOT NULL CHECK (advisory_implication <> ''),
    risk_flags TEXT[] NOT NULL DEFAULT '{}',
    invalidation TEXT NOT NULL CHECK (invalidation <> ''),
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS equity_impact_assessments_ticker_idx ON analyst.equity_impact_assessments (ticker);
CREATE INDEX IF NOT EXISTS equity_impact_assessments_event_ids_idx ON analyst.equity_impact_assessments USING gin (linked_event_ids);
CREATE INDEX IF NOT EXISTS equity_impact_assessments_evidence_ids_idx ON analyst.equity_impact_assessments USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS analyst.valuation_contexts (
    valuation_context_id TEXT PRIMARY KEY CHECK (valuation_context_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    valuation_state TEXT NOT NULL CHECK (valuation_state <> ''),
    forward_pe TEXT,
    ev_sales TEXT,
    assumptions TEXT[] NOT NULL DEFAULT '{}',
    risk_flags TEXT[] NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS valuation_contexts_ticker_idx ON analyst.valuation_contexts (ticker);
CREATE INDEX IF NOT EXISTS valuation_contexts_evidence_ids_idx ON analyst.valuation_contexts USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS analyst.macro_regime_snapshots (
    regime_id TEXT PRIMARY KEY CHECK (regime_id <> ''),
    risk_type TEXT NOT NULL CHECK (risk_type <> ''),
    status TEXT NOT NULL CHECK (status <> ''),
    linked_event_ids TEXT[] NOT NULL DEFAULT '{}',
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    summary TEXT NOT NULL CHECK (summary <> ''),
    portfolio_monitoring_note TEXT NOT NULL CHECK (portfolio_monitoring_note <> ''),
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS macro_regime_snapshots_event_ids_idx ON analyst.macro_regime_snapshots USING gin (linked_event_ids);
CREATE INDEX IF NOT EXISTS macro_regime_snapshots_evidence_ids_idx ON analyst.macro_regime_snapshots USING gin (evidence_ids);

CREATE TABLE IF NOT EXISTS analyst.trading_advisories (
    advisory_id TEXT PRIMARY KEY CHECK (advisory_id <> ''),
    recommendation_artifact_id TEXT,
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    advisory_label TEXT NOT NULL DEFAULT 'advisory_only' CHECK (advisory_label = 'advisory_only'),
    analyst_action TEXT NOT NULL CHECK (analyst_action IN ('watch', 'accumulate', 'hold', 'trim', 'avoid', 'review', 'exit-candidate')),
    advisory_summary TEXT NOT NULL CHECK (advisory_summary <> ''),
    evidence_ids TEXT[] NOT NULL CHECK (cardinality(evidence_ids) > 0),
    model_run_ids TEXT[] NOT NULL DEFAULT '{}',
    signal_bundle_id TEXT,
    target_weights_id TEXT,
    deterministic_checks TEXT[] NOT NULL DEFAULT '{}',
    linked_trade_plan_id TEXT,
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS trading_advisories_ticker_idx ON analyst.trading_advisories (ticker);
CREATE INDEX IF NOT EXISTS trading_advisories_evidence_ids_idx ON analyst.trading_advisories USING gin (evidence_ids);
CREATE INDEX IF NOT EXISTS trading_advisories_model_run_ids_idx ON analyst.trading_advisories USING gin (model_run_ids);

CREATE TABLE IF NOT EXISTS analyst.analyst_briefs (
    brief_id TEXT PRIMARY KEY CHECK (brief_id <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    title TEXT NOT NULL CHECK (title <> ''),
    advisory_label TEXT NOT NULL DEFAULT 'advisory_only' CHECK (advisory_label = 'advisory_only'),
    executive_summary TEXT NOT NULL CHECK (executive_summary <> ''),
    market_event_ids TEXT[] NOT NULL DEFAULT '{}',
    segment_impact_ids TEXT[] NOT NULL DEFAULT '{}',
    trading_advisory_ids TEXT[] NOT NULL DEFAULT '{}',
    model_run_ids TEXT[] NOT NULL DEFAULT '{}',
    payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS analyst_briefs_as_of_idx ON analyst.analyst_briefs (as_of DESC);
CREATE INDEX IF NOT EXISTS analyst_briefs_market_event_ids_idx ON analyst.analyst_briefs USING gin (market_event_ids);
