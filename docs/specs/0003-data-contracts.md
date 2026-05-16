# 0003 Data Contracts

## Purpose

Define the initial contract surface for Phase 1 implementation.

## Required Contracts

- `Position`
- `TradeEntry`
- `TradeJournal`
- `UniverseMember`
- `DatasetSnapshot`
- `EvidenceItem`
- `EvidenceClaim`
- `SourceSignal`
- `MarketEvent`
- `FinancialSnapshot`
- `ValuationContext`
- `MacroRegimeSnapshot`
- `FeatureSet`
- `ModelRun`
- `SignalBundle`
- `TargetWeights`
- `ImplementationEstimate`
- `BacktestRun`
- `ModelInventoryEntry`
- `RecommendationArtifact`
- `RecommendationAudit`
- `TradingAdvisory`
- `AdvisoryUpdate`
- `IncidentRecord`
- `DataQualityCheck`
- `RunArtifact`

## SourceSignal

`SourceSignal` represents a raw monitored signal from public internet, filings, financial data, macro data, analyst/news flow, or thematic source.

Required fields:

- `signal_id`
- `source_type`
- `source_uri`
- `publisher`
- `captured_at`
- `available_at`
- `tickers`
- `themes`
- `segments`
- `raw_summary`
- `data_class`
- `content_hash`
- `evidence_id`
- `confidence`

Rules:

- Must link to an `EvidenceItem` through `evidence_id`.
- Must include `content_hash`.
- Must preserve source timing with `captured_at` and `available_at`.
- Raw source signals are not advisory outputs and cannot directly become trading actions.

## MarketEvent

`MarketEvent` is a first-class advisory signal contract for catalyst-driven AI infrastructure analysis.

Required fields:

- `event_id`
- `event_type`
- `source_evidence_ids`
- `tickers`
- `companies`
- `themes`
- `catalyst`
- `ai_relevance`
- `direction`
- `time_horizon`
- `confidence`
- `occurred_at`
- `available_at`
- `content_hash`
- `extracted_by_model_run_id`
- `review_status`

## FinancialSnapshot

`FinancialSnapshot` represents latest company financial and valuation fundamentals.

Required fields:

- `ticker`
- `as_of`
- `revenue_growth`
- `gross_margin`
- `operating_margin`
- `free_cash_flow`
- `capex`
- `debt`
- `cash`
- `forward_pe`
- `ev_sales`
- `ev_ebitda`
- `analyst_estimate_revision`
- `source_evidence_ids`

Rules:

- Must include at least one `source_evidence_id`.
- Numeric fundamentals must come from deterministic ingestion, financial data transforms, filings, or explicitly sourced analyst-estimate data.
- LLMs may explain a FinancialSnapshot but must not calculate or overwrite values.

## ValuationContext

`ValuationContext` represents valuation interpretation, not final price truth.

Required fields:

- `ticker`
- `as_of`
- `valuation_summary`
- `peer_group`
- `valuation_multiples`
- `bear_case_assumptions`
- `base_case_assumptions`
- `bull_case_assumptions`
- `price_target_scenarios`
- `key_sensitivities`
- `risk_flags`
- `evidence_ids`
- `generated_by_model_run_id`
- `deterministic_inputs_hash`

Rules:

- Every material valuation claim must link to `evidence_ids`.
- `generated_by_model_run_id` must resolve to a governed ModelRun.
- `deterministic_inputs_hash` must cover the underlying financial, peer, and scenario inputs.
- Price targets are scenarios, not predictions.
- LLMs may generate valuation scenario explanation but may not own deterministic inputs.

## MacroRegimeSnapshot

`MacroRegimeSnapshot` represents macro and systemic context.

Required fields:

- `as_of`
- `rates_regime`
- `liquidity_regime`
- `risk_appetite`
- `semiconductor_cycle`
- `ai_capex_cycle`
- `credit_conditions`
- `energy_price_context`
- `geopolitical_risk_level`
- `evidence_ids`

Rules:

- Every macro/systemic regime claim must link to `evidence_ids`.
- Regime labels must be controlled values or explicitly marked review-needed.
- MacroRegimeSnapshot can inform interpretation, but deterministic code owns exposure and risk-limit checks.

## TradingAdvisory

`TradingAdvisory` is an advisory-only output for ticker or portfolio review.

Required fields:

- `advisory_id`
- `ticker_or_portfolio`
- `advisory_label`
- `analyst_action`
- `thesis_summary`
- `catalyst_summary`
- `valuation_context_id`
- `risk_regime_ids`
- `market_event_ids`
- `segment_impact_ids`
- `entry_zone`
- `add_zone`
- `invalidation_level`
- `target_scenarios`
- `time_horizon`
- `risk_flags`
- `evidence_ids`
- `model_run_ids`
- `deterministic_checks`
- `created_at`

Rules:

- `advisory_label` must be advisory-only.
- `analyst_action` must be one of `watch`, `accumulate`, `hold`, `trim`, `avoid`, or `review`.
- Must link to `evidence_ids`, `model_run_ids`, deterministic checks, and validated upstream context.
- Entry, add, trim, exit, and invalidation levels are planning guidance, not orders.
- Target scenarios are scenarios, not predictions.
- Deterministic code owns PnL, exposure, risk-limit checks, accounting, stale-data gates, and publication policy checks.

## AdvisoryUpdate

`AdvisoryUpdate` represents changes since a prior advisory brief.

Required fields:

- `update_id`
- `previous_advisory_id`
- `new_advisory_id`
- `what_changed`
- `thesis_change_direction`
- `risk_change_direction`
- `valuation_change_direction`
- `confidence_change`
- `evidence_ids`
- `created_at`

Rules:

- Must link to the previous and new advisory records.
- Must include `evidence_ids` for every material change.
- Change-direction fields must use controlled values.
- AdvisoryUpdate explains a delta; it does not create an executable trading action.

## Contract Rules

- IDs must be stable and audit-friendly.
- Source-derived records must include `content_hash`.
- Point-in-time records must include `as_of`, `available_at`, or equivalent.
- Recommendation artifacts must link to evidence, model runs, signals, and target weights.
- TradingAdvisory records must link to evidence, model runs, valuation context, risk regimes, market events, segment impacts, and deterministic checks.
- Portfolio holdings are relational facts, not vector-only records.
- Model outputs must be validated before persistence.
- MarketEvents must link to evidence.
- Events without provenance cannot influence `SignalBundle`.
- LLMs may extract events only through allowed model routes.
- Deterministic code owns scoring after event extraction.
- MarketEvents are advisory signals, not trading actions.
- all advisory outputs are advisory-only.
- every material claim links to evidence_ids.
- Price targets are scenarios, not predictions.
- Entry, add, trim, exit, and invalidation levels are planning guidance, not orders.
- Deterministic code owns PnL, exposure, risk-limit checks, and accounting.
- LLMs may generate narrative, thesis interpretation, risk critique, and valuation scenario explanation.
- No object may include broker, route, exchange, order_id, execution_id, or auto_trade fields.
