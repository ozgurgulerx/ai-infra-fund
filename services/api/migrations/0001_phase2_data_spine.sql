CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS evidence;
CREATE SCHEMA IF NOT EXISTS audit;
CREATE SCHEMA IF NOT EXISTS signals;
CREATE SCHEMA IF NOT EXISTS recommendations;
CREATE SCHEMA IF NOT EXISTS governance;

CREATE TABLE IF NOT EXISTS audit.schema_migrations (
    migration_name TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS core.positions (
    position_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    quantity NUMERIC NOT NULL,
    cost_basis NUMERIC,
    currency TEXT NOT NULL DEFAULT 'USD',
    account_label TEXT,
    asset_type TEXT NOT NULL CHECK (asset_type IN ('equity', 'etf', 'cash', 'future', 'option', 'crypto', 'other')),
    opened_at DATE,
    notes TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS positions_ticker_idx ON core.positions (ticker);
CREATE INDEX IF NOT EXISTS positions_account_label_idx ON core.positions (account_label);

CREATE TABLE IF NOT EXISTS core.trade_entries (
    trade_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    side TEXT NOT NULL CHECK (side IN ('buy', 'sell')),
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    price NUMERIC,
    fees NUMERIC NOT NULL DEFAULT 0 CHECK (fees >= 0),
    trade_date DATE NOT NULL,
    settlement_date DATE,
    account_label TEXT,
    status TEXT NOT NULL CHECK (status IN ('intended', 'paper', 'completed', 'cancelled', 'ignored')),
    source TEXT NOT NULL DEFAULT 'manual',
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS trade_entries_ticker_trade_date_idx ON core.trade_entries (ticker, trade_date);
CREATE INDEX IF NOT EXISTS trade_entries_status_idx ON core.trade_entries (status);
CREATE INDEX IF NOT EXISTS trade_entries_account_label_idx ON core.trade_entries (account_label);

CREATE TABLE IF NOT EXISTS core.portfolio_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    as_of TIMESTAMPTZ NOT NULL,
    cash_value NUMERIC NOT NULL DEFAULT 0,
    total_market_value NUMERIC NOT NULL,
    source TEXT NOT NULL,
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS portfolio_snapshots_content_hash_idx ON core.portfolio_snapshots (content_hash);
CREATE INDEX IF NOT EXISTS portfolio_snapshots_as_of_idx ON core.portfolio_snapshots (as_of);

CREATE TABLE IF NOT EXISTS core.portfolio_snapshot_positions (
    snapshot_id UUID NOT NULL REFERENCES core.portfolio_snapshots(snapshot_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    quantity NUMERIC NOT NULL,
    market_price NUMERIC,
    market_value NUMERIC,
    portfolio_weight NUMERIC,
    unrealized_pnl NUMERIC,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (snapshot_id, ticker)
);

CREATE INDEX IF NOT EXISTS portfolio_snapshot_positions_ticker_idx ON core.portfolio_snapshot_positions (ticker);

CREATE TABLE IF NOT EXISTS core.universe_members (
    ticker TEXT PRIMARY KEY CHECK (ticker <> ''),
    name TEXT,
    theme TEXT,
    role TEXT,
    watchlist_status TEXT,
    max_weight NUMERIC,
    liquidity_floor NUMERIC,
    thesis_source TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS universe_members_theme_idx ON core.universe_members (theme);
CREATE INDEX IF NOT EXISTS universe_members_watchlist_status_idx ON core.universe_members (watchlist_status);

CREATE TABLE IF NOT EXISTS audit.data_snapshots (
    snapshot_id TEXT PRIMARY KEY CHECK (snapshot_id <> ''),
    dataset_name TEXT NOT NULL CHECK (dataset_name <> ''),
    source TEXT NOT NULL CHECK (source <> ''),
    license_label TEXT NOT NULL CHECK (license_label <> ''),
    retrieved_at TIMESTAMPTZ NOT NULL,
    effective_at TIMESTAMPTZ,
    available_at TIMESTAMPTZ NOT NULL,
    storage_uri TEXT NOT NULL CHECK (storage_uri <> ''),
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    schema_version TEXT NOT NULL CHECK (schema_version <> ''),
    row_count INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS data_snapshots_content_hash_idx ON audit.data_snapshots (content_hash);
CREATE INDEX IF NOT EXISTS data_snapshots_dataset_available_at_idx ON audit.data_snapshots (dataset_name, available_at);
CREATE INDEX IF NOT EXISTS data_snapshots_source_idx ON audit.data_snapshots (source);

CREATE TABLE IF NOT EXISTS audit.model_runs (
    model_run_id TEXT PRIMARY KEY CHECK (model_run_id <> ''),
    task_role TEXT NOT NULL CHECK (task_role <> ''),
    model_id TEXT NOT NULL CHECK (model_id <> ''),
    deployment TEXT NOT NULL CHECK (deployment <> ''),
    provider TEXT NOT NULL CHECK (provider <> ''),
    prompt_version TEXT NOT NULL CHECK (prompt_version <> ''),
    input_hash TEXT NOT NULL CHECK (input_hash <> ''),
    output_hash TEXT,
    latency_ms INTEGER,
    token_estimate_input INTEGER,
    token_estimate_output INTEGER,
    cost_estimate NUMERIC,
    schema_valid BOOLEAN NOT NULL DEFAULT false,
    retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
    data_classes TEXT[] NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('success', 'retry', 'failure', 'denied')),
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS model_runs_task_role_idx ON audit.model_runs (task_role);
CREATE INDEX IF NOT EXISTS model_runs_model_id_idx ON audit.model_runs (model_id);
CREATE INDEX IF NOT EXISTS model_runs_prompt_version_idx ON audit.model_runs (prompt_version);
CREATE INDEX IF NOT EXISTS model_runs_status_idx ON audit.model_runs (status);
CREATE INDEX IF NOT EXISTS model_runs_created_at_idx ON audit.model_runs (created_at);
CREATE INDEX IF NOT EXISTS model_runs_data_classes_idx ON audit.model_runs USING gin (data_classes);

CREATE TABLE IF NOT EXISTS audit.run_artifacts (
    run_id TEXT PRIMARY KEY CHECK (run_id <> ''),
    run_type TEXT NOT NULL CHECK (run_type <> ''),
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    inputs_hash TEXT NOT NULL CHECK (inputs_hash <> ''),
    output_hash TEXT,
    artifact_uri TEXT,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS run_artifacts_run_type_idx ON audit.run_artifacts (run_type);
CREATE INDEX IF NOT EXISTS run_artifacts_status_idx ON audit.run_artifacts (status);
CREATE INDEX IF NOT EXISTS run_artifacts_started_at_idx ON audit.run_artifacts (started_at);

CREATE TABLE IF NOT EXISTS audit.backtest_runs (
    backtest_run_id TEXT PRIMARY KEY CHECK (backtest_run_id <> ''),
    strategy_id TEXT NOT NULL CHECK (strategy_id <> ''),
    dataset_snapshot_ids TEXT[] NOT NULL DEFAULT '{}',
    started_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,
    walk_forward_config_json JSONB NOT NULL DEFAULT '{}',
    summary_metrics_json JSONB NOT NULL DEFAULT '{}',
    transaction_cost_model_json JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed', 'cancelled')),
    error_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS backtest_runs_strategy_id_idx ON audit.backtest_runs (strategy_id);
CREATE INDEX IF NOT EXISTS backtest_runs_started_at_idx ON audit.backtest_runs (started_at);
CREATE INDEX IF NOT EXISTS backtest_runs_snapshot_ids_idx ON audit.backtest_runs USING gin (dataset_snapshot_ids);

CREATE TABLE IF NOT EXISTS evidence.evidence_items (
    evidence_id TEXT PRIMARY KEY CHECK (evidence_id <> ''),
    source_uri TEXT NOT NULL CHECK (source_uri <> ''),
    source_type TEXT NOT NULL CHECK (source_type <> ''),
    title TEXT,
    publisher TEXT,
    author TEXT,
    published_at TIMESTAMPTZ,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    license_label TEXT NOT NULL CHECK (license_label <> ''),
    data_class TEXT NOT NULL CHECK (data_class IN ('public_market_data', 'public_evidence', 'user_portfolio', 'private_research', 'run_audit', 'derived_analytics', 'secrets')),
    tickers TEXT[] NOT NULL DEFAULT '{}',
    themes TEXT[] NOT NULL DEFAULT '{}',
    summary TEXT,
    storage_uri TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS evidence_items_content_hash_idx ON evidence.evidence_items (content_hash);
CREATE INDEX IF NOT EXISTS evidence_items_published_at_idx ON evidence.evidence_items (published_at);
CREATE INDEX IF NOT EXISTS evidence_items_data_class_idx ON evidence.evidence_items (data_class);
CREATE INDEX IF NOT EXISTS evidence_items_tickers_idx ON evidence.evidence_items USING gin (tickers);
CREATE INDEX IF NOT EXISTS evidence_items_themes_idx ON evidence.evidence_items USING gin (themes);

CREATE TABLE IF NOT EXISTS evidence.evidence_chunks (
    chunk_id TEXT PRIMARY KEY CHECK (chunk_id <> ''),
    evidence_id TEXT NOT NULL REFERENCES evidence.evidence_items(evidence_id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
    chunk_text TEXT NOT NULL CHECK (chunk_text <> ''),
    span_ref TEXT,
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    embedding_model TEXT NOT NULL CHECK (embedding_model <> ''),
    embedding vector(1024),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS evidence_chunks_content_hash_idx ON evidence.evidence_chunks (content_hash);
CREATE UNIQUE INDEX IF NOT EXISTS evidence_chunks_evidence_index_idx ON evidence.evidence_chunks (evidence_id, chunk_index);
CREATE INDEX IF NOT EXISTS evidence_chunks_embedding_hnsw_idx ON evidence.evidence_chunks USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS evidence.evidence_claims (
    claim_id TEXT PRIMARY KEY CHECK (claim_id <> ''),
    evidence_id TEXT NOT NULL REFERENCES evidence.evidence_items(evidence_id) ON DELETE CASCADE,
    chunk_id TEXT REFERENCES evidence.evidence_chunks(chunk_id) ON DELETE SET NULL,
    ticker_or_theme TEXT NOT NULL CHECK (ticker_or_theme <> ''),
    claim_type TEXT NOT NULL CHECK (claim_type <> ''),
    direction TEXT,
    magnitude NUMERIC,
    time_horizon TEXT NOT NULL CHECK (time_horizon <> ''),
    confidence NUMERIC NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    quote_or_span_ref TEXT NOT NULL CHECK (quote_or_span_ref <> ''),
    extracted_by_model_run_id TEXT REFERENCES audit.model_runs(model_run_id),
    validated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS evidence_claims_ticker_or_theme_idx ON evidence.evidence_claims (ticker_or_theme);
CREATE INDEX IF NOT EXISTS evidence_claims_claim_type_idx ON evidence.evidence_claims (claim_type);
CREATE INDEX IF NOT EXISTS evidence_claims_evidence_id_idx ON evidence.evidence_claims (evidence_id);
CREATE INDEX IF NOT EXISTS evidence_claims_model_run_id_idx ON evidence.evidence_claims (extracted_by_model_run_id);

CREATE TABLE IF NOT EXISTS signals.feature_sets (
    feature_set_id TEXT PRIMARY KEY CHECK (feature_set_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    input_snapshot_hash TEXT NOT NULL CHECK (input_snapshot_hash <> ''),
    formula_versions JSONB NOT NULL DEFAULT '{}',
    features_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS feature_sets_ticker_as_of_idx ON signals.feature_sets (ticker, as_of);
CREATE INDEX IF NOT EXISTS feature_sets_available_at_idx ON signals.feature_sets (available_at);

CREATE TABLE IF NOT EXISTS signals.market_snapshots (
    market_snapshot_id TEXT PRIMARY KEY CHECK (market_snapshot_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    asset_type TEXT NOT NULL CHECK (asset_type IN ('equity', 'etf', 'cash', 'future', 'option', 'crypto', 'other')),
    as_of TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    source TEXT NOT NULL CHECK (source <> ''),
    open_price NUMERIC,
    high_price NUMERIC,
    low_price NUMERIC,
    close_price NUMERIC,
    adjusted_close_price NUMERIC,
    volume NUMERIC,
    content_hash TEXT NOT NULL CHECK (content_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS market_snapshots_content_hash_idx ON signals.market_snapshots (content_hash);
CREATE INDEX IF NOT EXISTS market_snapshots_ticker_as_of_idx ON signals.market_snapshots (ticker, as_of);
CREATE INDEX IF NOT EXISTS market_snapshots_available_at_idx ON signals.market_snapshots (available_at);

CREATE TABLE IF NOT EXISTS signals.factor_rows (
    factor_row_id TEXT PRIMARY KEY CHECK (factor_row_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    factor_set TEXT NOT NULL CHECK (factor_set <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    available_at TIMESTAMPTZ NOT NULL,
    factors_json JSONB NOT NULL DEFAULT '{}',
    formula_versions JSONB NOT NULL DEFAULT '{}',
    input_snapshot_hash TEXT NOT NULL CHECK (input_snapshot_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS factor_rows_ticker_as_of_idx ON signals.factor_rows (ticker, as_of);
CREATE INDEX IF NOT EXISTS factor_rows_factor_set_idx ON signals.factor_rows (factor_set);
CREATE INDEX IF NOT EXISTS factor_rows_available_at_idx ON signals.factor_rows (available_at);

CREATE TABLE IF NOT EXISTS signals.signal_bundles (
    signal_bundle_id TEXT PRIMARY KEY CHECK (signal_bundle_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    strategic_thesis_score NUMERIC NOT NULL,
    tactical_technical_score NUMERIC NOT NULL,
    forward_indicator_score NUMERIC NOT NULL,
    portfolio_risk_score NUMERIC NOT NULL,
    formula_versions JSONB NOT NULL DEFAULT '{}',
    input_snapshot_hash TEXT NOT NULL CHECK (input_snapshot_hash <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS signal_bundles_ticker_as_of_idx ON signals.signal_bundles (ticker, as_of);
CREATE INDEX IF NOT EXISTS signal_bundles_formula_versions_idx ON signals.signal_bundles USING gin (formula_versions);

CREATE TABLE IF NOT EXISTS signals.implementation_estimates (
    implementation_estimate_id TEXT PRIMARY KEY CHECK (implementation_estimate_id <> ''),
    ticker TEXT NOT NULL CHECK (ticker <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    average_daily_volume NUMERIC,
    spread_bps NUMERIC,
    slippage_bps NUMERIC,
    liquidity_score NUMERIC,
    capacity_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS implementation_estimates_ticker_as_of_idx ON signals.implementation_estimates (ticker, as_of);

CREATE TABLE IF NOT EXISTS recommendations.target_weights (
    target_weights_id TEXT PRIMARY KEY CHECK (target_weights_id <> ''),
    as_of TIMESTAMPTZ NOT NULL,
    portfolio_id TEXT,
    cash_weight NUMERIC NOT NULL CHECK (cash_weight >= 0 AND cash_weight <= 1),
    weights_json JSONB NOT NULL DEFAULT '{}',
    constraints_json JSONB NOT NULL DEFAULT '{}',
    source_signal_bundle_ids TEXT[] NOT NULL DEFAULT '{}',
    generated_by TEXT NOT NULL CHECK (generated_by <> '' AND generated_by NOT IN ('llm', 'raw_llm', 'cloud_model', 'model_output')),
    validation_status TEXT NOT NULL CHECK (validation_status <> ''),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS target_weights_as_of_idx ON recommendations.target_weights (as_of);
CREATE INDEX IF NOT EXISTS target_weights_validation_status_idx ON recommendations.target_weights (validation_status);
CREATE INDEX IF NOT EXISTS target_weights_signal_bundle_ids_idx ON recommendations.target_weights USING gin (source_signal_bundle_ids);

CREATE TABLE IF NOT EXISTS recommendations.recommendation_artifacts (
    recommendation_id TEXT PRIMARY KEY CHECK (recommendation_id <> ''),
    ticker_or_portfolio TEXT NOT NULL CHECK (ticker_or_portfolio <> ''),
    advisory_label TEXT NOT NULL CHECK (advisory_label = 'advisory_only'),
    action TEXT NOT NULL CHECK (action IN ('core_buy', 'accumulate', 'hold', 'watch', 'trim', 'avoid', 'exit_candidate')),
    horizon TEXT NOT NULL CHECK (horizon <> ''),
    score_breakdown_json JSONB NOT NULL DEFAULT '{}',
    target_weights_id TEXT NOT NULL REFERENCES recommendations.target_weights(target_weights_id),
    signal_bundle_id TEXT NOT NULL REFERENCES signals.signal_bundles(signal_bundle_id),
    evidence_ids TEXT[] NOT NULL,
    model_run_ids TEXT[] NOT NULL,
    risks_json JSONB NOT NULL DEFAULT '{}',
    contradictions_json JSONB,
    final_payload_json JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (array_length(evidence_ids, 1) > 0 AND cardinality(evidence_ids) > 0),
    CHECK (array_length(model_run_ids, 1) > 0 AND cardinality(model_run_ids) > 0)
);

CREATE INDEX IF NOT EXISTS recommendation_artifacts_ticker_idx ON recommendations.recommendation_artifacts (ticker_or_portfolio);
CREATE INDEX IF NOT EXISTS recommendation_artifacts_action_idx ON recommendations.recommendation_artifacts (action);
CREATE INDEX IF NOT EXISTS recommendation_artifacts_created_at_idx ON recommendations.recommendation_artifacts (created_at);
CREATE INDEX IF NOT EXISTS recommendation_artifacts_evidence_ids_idx ON recommendations.recommendation_artifacts USING gin (evidence_ids);
CREATE INDEX IF NOT EXISTS recommendation_artifacts_model_run_ids_idx ON recommendations.recommendation_artifacts USING gin (model_run_ids);

CREATE TABLE IF NOT EXISTS recommendations.recommendation_audits (
    audit_id TEXT PRIMARY KEY CHECK (audit_id <> ''),
    recommendation_id TEXT NOT NULL REFERENCES recommendations.recommendation_artifacts(recommendation_id),
    target_weights_id TEXT NOT NULL REFERENCES recommendations.target_weights(target_weights_id),
    signal_bundle_id TEXT NOT NULL REFERENCES signals.signal_bundles(signal_bundle_id),
    evidence_ids TEXT[] NOT NULL,
    model_run_ids TEXT[] NOT NULL,
    deterministic_checks_json JSONB NOT NULL DEFAULT '{}',
    reviewer_findings_json JSONB,
    schema_valid BOOLEAN NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (array_length(evidence_ids, 1) > 0 AND cardinality(evidence_ids) > 0),
    CHECK (array_length(model_run_ids, 1) > 0 AND cardinality(model_run_ids) > 0)
);

CREATE INDEX IF NOT EXISTS recommendation_audits_recommendation_id_idx ON recommendations.recommendation_audits (recommendation_id);
CREATE INDEX IF NOT EXISTS recommendation_audits_signal_bundle_id_idx ON recommendations.recommendation_audits (signal_bundle_id);
CREATE INDEX IF NOT EXISTS recommendation_audits_schema_valid_idx ON recommendations.recommendation_audits (schema_valid);

CREATE TABLE IF NOT EXISTS governance.model_inventory (
    model_inventory_id TEXT PRIMARY KEY CHECK (model_inventory_id <> ''),
    model_id TEXT NOT NULL CHECK (model_id <> ''),
    deployment TEXT NOT NULL CHECK (deployment <> ''),
    provider TEXT NOT NULL CHECK (provider <> ''),
    endpoint_type TEXT NOT NULL CHECK (endpoint_type <> ''),
    task_roles TEXT[] NOT NULL DEFAULT '{}',
    privacy_class TEXT NOT NULL CHECK (privacy_class <> ''),
    allowed_data_classes TEXT[] NOT NULL DEFAULT '{}',
    fallback_chain TEXT[] NOT NULL DEFAULT '{}',
    structured_output_support BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS model_inventory_model_id_idx ON governance.model_inventory (model_id);
CREATE INDEX IF NOT EXISTS model_inventory_task_roles_idx ON governance.model_inventory USING gin (task_roles);
CREATE INDEX IF NOT EXISTS model_inventory_data_classes_idx ON governance.model_inventory USING gin (allowed_data_classes);

CREATE TABLE IF NOT EXISTS governance.incident_records (
    incident_id TEXT PRIMARY KEY CHECK (incident_id <> ''),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    affected_artifacts TEXT[] NOT NULL DEFAULT '{}',
    freeze_status TEXT NOT NULL CHECK (freeze_status IN ('open', 'frozen', 'mitigated', 'resolved')),
    root_cause TEXT,
    remediation TEXT,
    reopen_criteria TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS incident_records_severity_idx ON governance.incident_records (severity);
CREATE INDEX IF NOT EXISTS incident_records_freeze_status_idx ON governance.incident_records (freeze_status);
CREATE INDEX IF NOT EXISTS incident_records_affected_artifacts_idx ON governance.incident_records USING gin (affected_artifacts);

CREATE TABLE IF NOT EXISTS governance.data_quality_checks (
    check_id TEXT PRIMARY KEY CHECK (check_id <> ''),
    dataset_id TEXT,
    check_name TEXT NOT NULL CHECK (check_name <> ''),
    status TEXT NOT NULL CHECK (status IN ('pass', 'warn', 'fail', 'stale', 'quarantined')),
    severity TEXT NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    observed_value TEXT,
    threshold TEXT,
    checked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS data_quality_checks_dataset_id_idx ON governance.data_quality_checks (dataset_id);
CREATE INDEX IF NOT EXISTS data_quality_checks_status_idx ON governance.data_quality_checks (status);
CREATE INDEX IF NOT EXISTS data_quality_checks_severity_idx ON governance.data_quality_checks (severity);
CREATE INDEX IF NOT EXISTS data_quality_checks_checked_at_idx ON governance.data_quality_checks (checked_at);

CREATE TABLE IF NOT EXISTS governance.data_entitlements (
    entitlement_id TEXT PRIMARY KEY CHECK (entitlement_id <> ''),
    source_name TEXT NOT NULL CHECK (source_name <> ''),
    license_label TEXT NOT NULL CHECK (license_label <> ''),
    allowed_uses TEXT[] NOT NULL DEFAULT '{}',
    cloud_model_allowed BOOLEAN NOT NULL DEFAULT false,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS data_entitlements_source_name_idx ON governance.data_entitlements (source_name);
CREATE INDEX IF NOT EXISTS data_entitlements_license_label_idx ON governance.data_entitlements (license_label);
