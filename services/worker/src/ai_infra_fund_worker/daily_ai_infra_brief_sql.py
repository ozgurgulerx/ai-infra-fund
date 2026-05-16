from __future__ import annotations


LATEST_SOURCE_SIGNALS_SQL = """
SELECT
    signal_id,
    source_type,
    signal_category,
    title,
    available_at,
    tickers,
    themes,
    evidence_ids,
    derived_market_event_ids,
    confidence,
    review_status
FROM analyst.source_signals
ORDER BY available_at DESC, signal_id ASC
LIMIT %s;
"""


LATEST_MARKET_EVENTS_SQL = """
SELECT
    event_id,
    event_type,
    source_signal_ids,
    evidence_ids,
    tickers,
    companies,
    themes,
    catalyst,
    ai_relevance,
    direction,
    time_horizon,
    confidence,
    available_at,
    extracted_by_model_run_id,
    review_status
FROM analyst.market_events
ORDER BY available_at DESC, event_id ASC
LIMIT %s;
"""


LATEST_SEGMENT_IMPACTS_SQL = """
SELECT
    segment_id,
    segment_name,
    primary_tickers,
    second_order_tickers,
    linked_event_ids,
    impact_direction,
    impact_summary,
    evidence_ids
FROM analyst.segment_impacts
ORDER BY segment_id ASC
LIMIT %s;
"""


LATEST_EQUITY_ASSESSMENTS_SQL = """
SELECT
    assessment_id,
    ticker,
    company,
    linked_event_ids,
    assessment,
    watch_items,
    advisory_implication,
    risk_flags,
    invalidation,
    evidence_ids
FROM analyst.equity_impact_assessments
ORDER BY created_at DESC, ticker ASC, assessment_id ASC
LIMIT %s;
"""


LATEST_VALUATION_CONTEXTS_SQL = """
SELECT
    valuation_context_id,
    ticker,
    valuation_state,
    assumptions,
    risk_flags,
    evidence_ids
FROM analyst.valuation_contexts
ORDER BY created_at DESC, ticker ASC, valuation_context_id ASC
LIMIT %s;
"""


LATEST_RISK_REGIME_SQL = """
SELECT
    regime_id,
    risk_type,
    status,
    severity,
    confidence,
    linked_event_ids,
    affected_segments,
    affected_tickers,
    evidence_ids,
    summary,
    available_at
FROM analyst.risk_regime_updates
ORDER BY available_at DESC, regime_id ASC
LIMIT %s;
"""


LATEST_TRADE_PLANS_SQL = """
SELECT
    trade_plan_id,
    ticker,
    status,
    advisory_action,
    linked_event_ids,
    readiness,
    blocking_reasons,
    manual_journal_only,
    evidence_ids,
    linked_advisory_id,
    last_reviewed_at
FROM analyst.trade_plans
ORDER BY last_reviewed_at DESC NULLS LAST, created_at DESC, trade_plan_id ASC
LIMIT %s;
"""


LATEST_PORTFOLIO_SNAPSHOT_SQL = """
SELECT
    snapshot_id,
    as_of,
    advisory_label,
    position_count,
    positions_json,
    concentration_flags,
    stale_price_flags
FROM analyst.portfolio_exposure_snapshots
ORDER BY as_of DESC, created_at DESC
LIMIT 1;
"""


LATEST_OUTCOMES_SQL = """
SELECT
    outcome_id,
    manual_journal_entry_id,
    advisory_id,
    ticker,
    market_event_ids,
    evidence_ids,
    outcome_label,
    reviewed_at,
    advisory_label
FROM analyst.outcome_journal_entries
ORDER BY available_at DESC, reviewed_at DESC, outcome_id ASC
LIMIT %s;
"""


EVIDENCE_BY_IDS_SQL = """
SELECT
    evidence_id,
    data_class,
    ingested_at,
    published_at,
    content_hash
FROM evidence.evidence_items
WHERE evidence_id = ANY(%s::text[])
ORDER BY evidence_id ASC;
"""


UPSERT_TRADING_ADVISORY_SQL = """
INSERT INTO analyst.trading_advisories (
    advisory_id,
    recommendation_artifact_id,
    ticker,
    advisory_label,
    analyst_action,
    advisory_summary,
    evidence_ids,
    model_run_ids,
    signal_bundle_id,
    target_weights_id,
    deterministic_checks,
    linked_trade_plan_id,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (advisory_id) DO UPDATE SET
    recommendation_artifact_id = EXCLUDED.recommendation_artifact_id,
    ticker = EXCLUDED.ticker,
    advisory_label = EXCLUDED.advisory_label,
    analyst_action = EXCLUDED.analyst_action,
    advisory_summary = EXCLUDED.advisory_summary,
    evidence_ids = EXCLUDED.evidence_ids,
    model_run_ids = EXCLUDED.model_run_ids,
    signal_bundle_id = EXCLUDED.signal_bundle_id,
    target_weights_id = EXCLUDED.target_weights_id,
    deterministic_checks = EXCLUDED.deterministic_checks,
    linked_trade_plan_id = EXCLUDED.linked_trade_plan_id,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_ANALYST_BRIEF_SQL = """
INSERT INTO analyst.analyst_briefs (
    brief_id,
    as_of,
    title,
    advisory_label,
    executive_summary,
    market_event_ids,
    segment_impact_ids,
    trading_advisory_ids,
    model_run_ids,
    payload_json,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
) ON CONFLICT (brief_id) DO UPDATE SET
    as_of = EXCLUDED.as_of,
    title = EXCLUDED.title,
    advisory_label = EXCLUDED.advisory_label,
    executive_summary = EXCLUDED.executive_summary,
    market_event_ids = EXCLUDED.market_event_ids,
    segment_impact_ids = EXCLUDED.segment_impact_ids,
    trading_advisory_ids = EXCLUDED.trading_advisory_ids,
    model_run_ids = EXCLUDED.model_run_ids,
    payload_json = EXCLUDED.payload_json,
    created_at = EXCLUDED.created_at;
"""


UPSERT_RUN_ARTIFACT_SQL = """
INSERT INTO audit.run_artifacts (
    run_id,
    run_type,
    started_at,
    completed_at,
    inputs_hash,
    output_hash,
    artifact_uri,
    status,
    error_summary,
    created_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
) ON CONFLICT (run_id) DO UPDATE SET
    run_type = EXCLUDED.run_type,
    started_at = EXCLUDED.started_at,
    completed_at = EXCLUDED.completed_at,
    inputs_hash = EXCLUDED.inputs_hash,
    output_hash = EXCLUDED.output_hash,
    artifact_uri = EXCLUDED.artifact_uri,
    status = EXCLUDED.status,
    error_summary = EXCLUDED.error_summary,
    created_at = EXCLUDED.created_at;
"""
