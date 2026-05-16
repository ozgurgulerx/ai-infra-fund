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
- `SegmentImpact`
- `EquityImpactAssessment`
- `FinancialSnapshot`
- `ValuationContext`
- `MacroRegimeSnapshot`
- `RiskRegimeUpdate`
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
- `TradePlan`
- `PortfolioExposureSnapshot`
- `AnalystBrief`
- `AdvisoryUpdate`
- `OutcomeJournalEntry`
- `LLMAnalystNote`
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

Rules:

- Must include at least one `source_evidence_id`.
- Must include `content_hash` for source-derived records.
- Event themes must resolve to at least one canonical AI infrastructure segment before the event can be marked usable.
- `extracted_by_model_run_id` must resolve to a governed ModelRun when the event was model-extracted.
- Events without provenance cannot influence `SegmentImpact`, `SignalBundle`, trade plans, or recommendation artifacts.
- MarketEvents are advisory signals, not trading actions.

## SegmentImpact

`SegmentImpact` maps validated MarketEvents into AI infrastructure stack segments and first-order or second-order ticker implications.

Required fields:

- `segment_id`
- `segment_name`
- `linked_event_ids`
- `primary_tickers`
- `first_order_tickers`
- `second_order_tickers`
- `impact_direction`
- `impact_summary`
- `confidence`
- `time_horizon`
- `risk_flags`
- `invalidation_condition`
- `latest_evidence_at`
- `source_evidence_ids`

Optional or conditional fields:

- `signal_bundle_id`
- `model_run_ids`

Rules:

- Must link to at least one validated `MarketEvent`.
- Must include `source_evidence_ids`; inherited event provenance should be materialized for audit.
- `first_order_tickers` and `second_order_tickers` must be distinguishable.
- `segment_id` must be a canonical AI infrastructure segment.
- `model_run_ids` must be present when the segment mapping or impact narrative is model-derived.
- SegmentImpact is an advisory analysis object and cannot create an executable trading action.

## EquityImpactAssessment

`EquityImpactAssessment` defines the current evidence-backed thesis state for one equity.

Required fields:

- `assessment_id`
- `ticker`
- `company`
- `linked_event_ids`
- `segment_ids`
- `assessment`
- `bull_case`
- `base_case`
- `bear_case`
- `risk_flags`
- `invalidation_condition`
- `watch_items`
- `advisory_implication`
- `confidence`
- `as_of`
- `source_evidence_ids`
- `model_run_ids`

Optional or conditional fields:

- `linked_signal_bundle_id`
- `linked_recommendation_artifact_id`

Rules:

- Must link to validated MarketEvents or direct evidence.
- Bull, base, bear, risk, and invalidation claims must be evidence-backed.
- `model_run_ids` must cover LLM-authored thesis narrative or critique.
- Any advisory implication must link to deterministic signal and recommendation artifacts before publication.
- LLM narrative cannot override deterministic scores, suppressions, risk constraints, target weights, or recommendation gates.

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

## RiskRegimeUpdate

`RiskRegimeUpdate` captures market, policy, supply-chain, power, capex, or portfolio risk-regime changes that affect analyst interpretation.

Required fields:

- `regime_id`
- `risk_type`
- `status`
- `severity`
- `confidence`
- `linked_event_ids`
- `affected_segments`
- `affected_tickers`
- `summary`
- `portfolio_monitoring_note`
- `relief_condition`
- `invalidation_condition`
- `as_of`
- `available_at`
- `source_evidence_ids`

Rules:

- Must link to validated MarketEvents or direct evidence through `linked_event_ids` and `source_evidence_ids`.
- `risk_type` and `status` must be controlled values.
- Elevated or stressed risk regimes must include monitoring, relief, or invalidation context.
- Risk regime updates can trigger review, but deterministic code owns risk constraints, exposure math, and publication gates.
- RiskRegimeUpdate is advisory-only and cannot imply broker transmission, routing, or market-action automation.

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
- Advisory payloads and deterministic check payloads must not include broker, route, exchange, order_id, execution_id, or auto_trade fields.

## TradePlan

`TradePlan` represents advisory-only planning guidance for local manual journal review.

Required fields:

- `trade_plan_id`
- `ticker`
- `company`
- `status`
- `advisory_action`
- `linked_event_ids`
- `linked_signal_bundle_id`
- `linked_recommendation_artifact_id`
- `entry_exit_levels_id`
- `price_target_scenario_id`
- `target_weights_id`
- `deterministic_check_ids`
- `readiness`
- `blocking_reasons`
- `manual_journal_only`
- `last_reviewed_at`

Rules:

- `manual_journal_only` must be true.
- Must link to evidence-backed MarketEvents, a SignalBundle, a recommendation artifact, deterministic checks, and local planning levels where available.
- Any blocked or stale plan must include `blocking_reasons`.
- Entry, add, trim, exit, and invalidation levels are planning guidance, not orders.
- TradePlan must not encode broker, routing, fill, external transmission, or automated market-action state.

## PortfolioExposureSnapshot

`PortfolioExposureSnapshot` represents deterministic portfolio exposure, concentration, correlation, and PnL context for the analyst workstation.

Required fields:

- `snapshot_id`
- `as_of`
- `currency`
- `source`
- `advisory_label`
- `total_market_value`
- `cash_placeholder`
- `gross_equity_exposure`
- `position_count`
- `positions`
- `correlation_exposure_ids`
- `pnl_summary_id`
- `target_weights_id`
- `concentration_flags`
- `stale_price_flags`

Position fields:

- `ticker`
- `company`
- `segment_tags`
- `market_value`
- `portfolio_weight`
- `cost_basis`
- `unrealized_pnl`
- `open_trade_plan_id`
- `risk_flags`
- `last_price_timestamp`

Rules:

- `advisory_label` must be advisory-only.
- `position_count` must equal the number of positions.
- Market value, exposure, portfolio weight, and PnL values are deterministic outputs, not LLM outputs.
- Missing or stale price state must be visible and must block balancing suggestions where material.
- Snapshot payloads must not include broker account, route, fill, or execution state.

## AnalystBrief

`AnalystBrief` synthesizes validated analyst state into daily or intraday cockpit output.

Required fields:

- `brief_id`
- `as_of`
- `generated_at`
- `title`
- `advisory_label`
- `executive_summary`
- `highest_conviction_theme_updates`
- `ticker_focus_list`
- `open_questions`
- `next_review_triggers`
- `market_event_ids`
- `segment_impact_ids`
- `risk_regime_update_ids`
- `suggested_action_ids`
- `model_run_ids`
- `freshness_status`

Rules:

- `advisory_label` must be visible and advisory-only.
- Briefs must link to evidence-backed MarketEvents or downstream objects.
- LLM-authored brief text must link to `model_run_ids` and cannot alter deterministic rankings, scores, exposure, target weights, PnL, or readiness gates.
- Missing evidence, stale inputs, unresolved contradictions, or failed deterministic checks must remain visible in the brief.
- AnalystBrief cannot include execution-language instructions.

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
- AdvisoryUpdate is advisory-only and cannot imply execution, routing, broker transmission, or auto-trading.

## OutcomeJournalEntry

`OutcomeJournalEntry` captures local-only manual analyst records and outcome review for intended or completed manual trades.

Required fields:

- `outcome_entry_id`
- `trade_entry_id`
- `ticker`
- `entry_type`
- `local_only`
- `linked_trade_plan_id`
- `advisory_label_at_time`
- `recorded_at`
- `evidence_available_ids`
- `market_event_ids_available_at_decision`
- `outcome_label`

Optional or conditional fields:

- `recorded_price`
- `recorded_quantity`
- `pnl_id`
- `realized_pnl`
- `unrealized_pnl`
- `plan_adherence_status`
- `analyst_note`
- `llm_review_note_id`

Rules:

- `local_only` must be true.
- Journal entries must not transmit to a broker or external trading system.
- Must preserve evidence and MarketEvents available at decision time.
- PnL and plan-adherence fields must come from deterministic accounting and comparison logic.
- LLMs may critique outcomes or draft lessons learned but must not calculate PnL or accounting values.

## LLMAnalystNote

`LLMAnalystNote` stores a bounded model-authored explanation, critique, summary, or review note tied to specific analyst objects.

Required fields:

- `note_id`
- `model_run_id`
- `scope`
- `allowed_role`
- `reviewed_object_ids`
- `evidence_ids`
- `note`
- `deterministic_fields_not_modified`
- `created_at`
- `review_status`

Rules:

- Must link to a governed `ModelRun`.
- Must use an allowed analyst role.
- Must link to reviewed objects or evidence.
- Must list protected deterministic fields when the note discusses scores, risk, target weights, levels, exposure, or PnL.
- LLMAnalystNote can explain, critique, or review; it cannot modify deterministic fields or create market-action instructions.

## Contract Rules

- IDs must be stable and audit-friendly.
- Source-derived records must include `content_hash`.
- Point-in-time records must include `as_of`, `available_at`, or equivalent.
- Recommendation artifacts must link to evidence, model runs, signals, and target weights.
- TradingAdvisory records must link to evidence, model runs, valuation context, risk regimes, market events, segment impacts, and deterministic checks.
- SegmentImpact records must link to evidence-backed MarketEvents and materialized `source_evidence_ids`.
- EquityImpactAssessment records must link to evidence, MarketEvents, segments, and model runs for model-authored thesis narrative.
- OutcomeJournalEntry records are local-only manual journal records and must preserve evidence available at decision time.
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
