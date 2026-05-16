# Analyst Object Model

## Purpose

This document defines the shared analyst object model implied by `docs/UI_SCREEN_SPECS.md` and `docs/mock_data/situational_awareness_brief.example.json`.

The model supports an AI Infrastructure Trading Analyst Workstation. It is advisory-only, evidence-backed, portfolio-aware, and local-journal-oriented. It is not a broker model, execution model, order model, or backtesting-first quant model.

## Boundary Rules

- No broker integration.
- No live order placement.
- No execution UI.
- No order tickets, route controls, submit buttons, fill states, or broker account views.
- Manual trade entry is local journal only.
- LLMs may classify, extract, summarize, review, critique, and explain.
- LLMs may generate narrative, thesis interpretation, risk critique, and valuation scenario explanation.
- LLMs must not own final scores, risk, constraints, target weights, portfolio exposure, entry/exit levels, or PnL calculations.
- Deterministic code owns scores, risk, constraints, target weights, correlation exposure, concentration checks, entry/exit levels, scenario values, PnL, exposure, risk-limit checks, and accounting.
- Every recommendation-like label must link to evidence and audit records where available.
- all advisory outputs are advisory-only.
- every material claim links to evidence_ids or source evidence references.
- Price targets are scenarios, not predictions.
- Entry, add, trim, exit, and invalidation levels are planning guidance, not orders.
- No object may include broker, route, exchange, order_id, execution_id, or auto_trade fields.

## Consumed Screens

- Daily Trading Cockpit
- AI Infrastructure Ecosystem Map
- Live Market / Sentiment Radar
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer
- Trade Journal + PnL Review

## LLM Analyst Roles

- `market_event_extractor`: creates draft `MarketEvent` objects from evidence.
- `source_signal_monitor`: records raw monitored `SourceSignal` objects from public and licensed source lanes.
- `market_event_reviewer`: reviews extracted events for provenance, clarity, and advisory wording.
- `fundamental_snapshot_reviewer`: explains `FinancialSnapshot` inputs without changing deterministic values.
- `valuation_context_analyst`: drafts valuation scenario interpretation for `ValuationContext`.
- `macro_regime_reviewer`: explains `MacroRegimeSnapshot` conditions and critiques risk framing.
- `segment_mapper`: creates or reviews draft `SegmentImpact` summaries from validated events.
- `equity_thesis_analyst`: creates or reviews narrative parts of `EquityImpactAssessment`.
- `risk_regime_reviewer`: reviews `RiskRegimeUpdate` explanations and relief conditions.
- `trading_advisory_synthesizer`: drafts advisory-only `TradingAdvisory` narrative from validated upstream objects.
- `trade_plan_critic`: reviews `TradePlan` consistency and drafts local journal notes.
- `portfolio_exposure_explainer`: explains `PortfolioExposureSnapshot` outputs without changing deterministic values.
- `brief_synthesizer`: creates narrative `AnalystBrief` summaries from validated upstream objects.
- `outcome_reviewer`: reviews `OutcomeJournalEntry` outcomes and drafts lessons learned.
- `llm_note_reviewer`: reviews `LLMAnalystNote` compliance and advisory-only language.

## Shared Validation Rules

- IDs must be stable, unique within object type, and audit-friendly.
- Timestamps must be ISO 8601 with timezone.
- Any object that influences a recommendation, trade plan, or risk state must link to evidence directly or through validated upstream objects.
- Referenced IDs must resolve to objects in the same run, persisted store, or audit ledger.
- Objects with stale evidence must remain renderable but cannot be marked review-ready.
- Any missing evidence, missing deterministic check, stale level, or unresolved contradiction must block action readiness.
- UI consumers must render fields as provided. They must not compute scores, weights, PnL, target prices, entry/exit levels, or constraints.
- Price targets and target scenarios must be displayed as scenario ranges or cases, never as predictions.
- Entry zones, add zones, invalidation levels, and exit planning labels must be displayed as planning guidance, never as orders.
- Source-derived records must preserve `content_hash` and evidence linkage before they influence advisory outputs.

## SourceSignal

### Purpose

Represents a raw monitored signal from public internet, filings, financial data, macro data, analyst/news flow, or thematic source.

### Fields

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

### Required Fields

- `signal_id`
- `source_type`
- `source_uri`
- `publisher`
- `captured_at`
- `available_at`
- `raw_summary`
- `data_class`
- `content_hash`
- `evidence_id`
- `confidence`

### Evidence Requirements

- Must link to exactly one canonical `EvidenceItem` through `evidence_id`.
- Any ticker, theme, segment, or source summary claim must be traceable to the linked evidence.
- Must preserve `content_hash` for source-derived deduplication and audit.

### Validation Rules

- `available_at` must not be earlier than `captured_at`.
- `source_type` and `data_class` must be controlled values.
- `confidence` must be bounded and cannot substitute for evidence.
- SourceSignal records are raw monitored inputs, not trading advice.

### Consumed By Screens

- Daily Trading Cockpit
- Live Market / Sentiment Radar
- Ticker Analyst Workbench

### LLM Analyst Role

- Create: `source_signal_monitor` may summarize source content into `raw_summary`.
- Review: `market_event_reviewer` or `llm_note_reviewer`.

### Deterministic Fields

- `signal_id`
- `captured_at`
- `available_at`
- `data_class`
- `content_hash`
- evidence link integrity
- duplicate detection

## FinancialSnapshot

### Purpose

Represents latest company financial and valuation fundamentals used by the analyst workstation.

### Fields

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

### Required Fields

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

### Evidence Requirements

- Must include at least one `source_evidence_id`.
- Every numeric value must trace to filings, financial data, analyst-estimate data, or a documented deterministic transform.
- Estimate revisions must preserve source evidence and point-in-time availability.

### Validation Rules

- `ticker` must be in the universe or explicit watchlist.
- `as_of` must represent the financial data timestamp, not UI render time.
- Missing, stale, or conflicting fundamentals must be visible to advisory consumers.
- LLMs may explain values but must not calculate or overwrite fundamentals.

### Consumed By Screens

- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer

### LLM Analyst Role

- Create: none for numeric values.
- Review: `fundamental_snapshot_reviewer` may explain trends and data gaps.

### Deterministic Fields

- `ticker`
- `as_of`
- all numeric fundamentals
- source evidence link integrity
- freshness and stale-data flags

## ValuationContext

### Purpose

Represents valuation interpretation, not final price truth.

### Fields

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

### Required Fields

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

### Evidence Requirements

- Must include `evidence_ids` for every material valuation claim.
- Peer group, multiple selection, assumptions, sensitivities, and risk flags must be evidence-backed.
- Price targets are scenarios, not predictions.

### Validation Rules

- `deterministic_inputs_hash` must cover the underlying financial inputs, peer data, and deterministic scenario inputs.
- `generated_by_model_run_id` must resolve to a governed `ModelRun`.
- `price_target_scenarios` must be labeled as bear, base, bull, or explicit custom cases.
- ValuationContext cannot mark an entry, add, trim, or exit action as executable.

### Consumed By Screens

- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer

### LLM Analyst Role

- Create: `valuation_context_analyst` may draft valuation summary and scenario explanation.
- Review: `llm_note_reviewer`.

### Deterministic Fields

- `ticker`
- `as_of`
- `valuation_multiples` when supplied by deterministic data transforms
- `deterministic_inputs_hash`
- scenario input values
- evidence link integrity

## MacroRegimeSnapshot

### Purpose

Represents macro and systemic context for advisory interpretation.

### Fields

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

### Required Fields

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

### Evidence Requirements

- Must include evidence for every macro or systemic regime claim.
- Cycle, liquidity, credit, energy, and geopolitical labels must be traceable to source evidence or deterministic regime rules.

### Validation Rules

- `as_of` must represent the regime observation time.
- Regime labels must be controlled values or include an explicit review-needed status.
- MacroRegimeSnapshot can change advisory interpretation, but deterministic code owns exposure and risk-limit checks.

### Consumed By Screens

- Daily Trading Cockpit
- Live Market / Sentiment Radar
- Portfolio + Exposure Balancer

### LLM Analyst Role

- Create: `macro_regime_reviewer` may summarize and critique macro context.
- Review: `risk_regime_reviewer`.

### Deterministic Fields

- `as_of`
- regime labels when rule-derived
- freshness state
- evidence link integrity

## TradingAdvisory

### Purpose

Represents an advisory-only output for a ticker or portfolio review.

### Fields

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

### Required Fields

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
- `target_scenarios`
- `time_horizon`
- `risk_flags`
- `evidence_ids`
- `model_run_ids`
- `deterministic_checks`
- `created_at`

### Evidence Requirements

- Must include `evidence_ids` for every material thesis, catalyst, valuation, risk, entry-zone, add-zone, invalidation, and target-scenario claim.
- `valuation_context_id`, `risk_regime_ids`, `market_event_ids`, and `segment_impact_ids` must resolve to validated upstream objects.
- `model_run_ids` must cover LLM-authored narrative or critique.

### Validation Rules

- `advisory_label` must be advisory-only.
- `analyst_action` must be one of watch, accumulate, hold, trim, avoid, or review.
- `entry_zone`, `add_zone`, and `invalidation_level` are planning guidance, not orders.
- `target_scenarios` are scenarios, not predictions.
- `deterministic_checks` must include risk, exposure, stale-data, and policy-gate results before publication.

### Consumed By Screens

- Daily Trading Cockpit
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: `trading_advisory_synthesizer` may draft thesis, catalyst, risk, and valuation explanation.
- Review: `llm_note_reviewer`.

### Deterministic Fields

- `advisory_id`
- `advisory_label`
- `analyst_action` after publication policy
- `entry_zone`
- `add_zone`
- `invalidation_level`
- `target_scenarios`
- `deterministic_checks`
- risk-limit, exposure, PnL, and accounting checks

## AdvisoryUpdate

### Purpose

Represents changes since a prior advisory brief.

### Fields

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

### Required Fields

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

### Evidence Requirements

- Must include `evidence_ids` for every material change explanation.
- Both advisory references must resolve to advisory-only `TradingAdvisory` records.

### Validation Rules

- Change-direction fields must be controlled values.
- `confidence_change` must distinguish increased, decreased, unchanged, and review-needed states.
- AdvisoryUpdate cannot create a new trading action by itself; it only explains the delta between advisory records.

### Consumed By Screens

- Daily Trading Cockpit
- Ticker Analyst Workbench
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: `brief_synthesizer` or `trading_advisory_synthesizer` may summarize deltas.
- Review: `llm_note_reviewer`.

### Deterministic Fields

- `update_id`
- advisory reference integrity
- created timestamp
- change-direction normalization when rule-derived

## MarketEvent

### Purpose

Represents a source-backed catalyst relevant to AI infrastructure equities.

### Fields

- `event_id`
- `event_type`
- `source_evidence_ids`
- `tickers`
- `companies`
- `themes`
- `segments`
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

### Required Fields

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
- `review_status`

### Evidence Requirements

- Must include at least one `source_evidence_id`.
- Must include `content_hash` for source-derived records.
- Any catalyst, ticker linkage, or AI relevance claim must be traceable to evidence.

### Validation Rules

- `available_at` must not be earlier than `occurred_at`.
- `event_type`, `direction`, `time_horizon`, and `review_status` must be controlled values.
- `review_status` must separate usable events from pending, rejected, quarantined, or stale events.
- Events without provenance cannot influence segment impact, signal bundles, trade plans, or recommendation artifacts.

### Consumed By Screens

- Daily Trading Cockpit
- AI Infrastructure Ecosystem Map
- Live Market / Sentiment Radar
- Ticker Analyst Workbench
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: `market_event_extractor`
- Review: `market_event_reviewer`

### Deterministic Fields

- `event_id`
- `content_hash`
- `occurred_at`
- `available_at`
- schema validity
- source evidence link integrity
- review gating after validation

## SegmentImpact

### Purpose

Maps validated MarketEvents into AI infrastructure stack segments and identifies first-order or second-order ticker implications.

### Fields

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
- `signal_bundle_id`
- `source_evidence_ids`
- `model_run_ids`

### Required Fields

- `segment_id`
- `segment_name`
- `linked_event_ids`
- `impact_direction`
- `impact_summary`
- `primary_tickers`
- `first_order_tickers`
- `second_order_tickers`
- `confidence`
- `time_horizon`
- `risk_flags`
- `invalidation_condition`
- `latest_evidence_at`
- `source_evidence_ids`

### Evidence Requirements

- Must link to at least one validated `MarketEvent`.
- Segment state, ticker implication, and risk claims must inherit evidence through linked events and materialized `source_evidence_ids`.
- `model_run_ids` must be present when the segment mapping or narrative is model-derived.

### Validation Rules

- `segment_id` must be a canonical AI infrastructure segment.
- Every `linked_event_id` must resolve to a validated MarketEvent or be marked review-needed.
- First-order and second-order tickers must be distinguishable.
- Segment impact cannot be marked complete without evidence freshness.

### Consumed By Screens

- Daily Trading Cockpit
- AI Infrastructure Ecosystem Map
- Ticker Analyst Workbench
- Portfolio + Exposure Balancer

### LLM Analyst Role

- Create: `segment_mapper` for narrative summaries and draft mappings.
- Review: `segment_mapper` or `market_event_reviewer`.

### Deterministic Fields

- `segment_id`
- canonical segment membership
- event counts
- first-order and second-order classification when supplied by rules
- `signal_bundle_id`
- `source_evidence_ids`
- `model_run_ids` when model-derived
- evidence freshness status
- downstream segment score or state

## EquityImpactAssessment

### Purpose

Defines the current evidence-backed thesis state for one equity.

### Fields

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
- `linked_signal_bundle_id`
- `linked_recommendation_artifact_id`
- `model_run_ids`

### Required Fields

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
- `as_of`
- `source_evidence_ids`
- `model_run_ids`

### Evidence Requirements

- Must link to validated MarketEvents or direct evidence.
- Bull, base, bear, risk, and invalidation claims must be evidence-backed.
- Any advisory implication must link to deterministic signal and recommendation artifacts before publication.

### Validation Rules

- `ticker` must be in the AI infrastructure universe or explicit watchlist.
- Assessment is incomplete if risk flags or invalidation are missing.
- Advisory labels must remain advisory-only.
- LLM narrative cannot override deterministic scores, suppressions, or recommendation gating.

### Consumed By Screens

- Daily Trading Cockpit
- AI Infrastructure Ecosystem Map
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer

### LLM Analyst Role

- Create: `equity_thesis_analyst` for thesis narrative and critique.
- Review: `equity_thesis_analyst` and `risk_regime_reviewer`.

### Deterministic Fields

- `assessment_id`
- `ticker`
- universe membership
- signal bundle linkage
- recommendation artifact linkage
- advisory label after deterministic publication checks
- risk suppressions
- confidence score if numeric or thresholded

## RiskRegimeUpdate

### Purpose

Captures changes in market, policy, supply-chain, power, capex, or portfolio risk regimes that affect interpretation of events and trade plans.

### Fields

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

### Required Fields

- `regime_id`
- `risk_type`
- `status`
- `linked_event_ids`
- `summary`
- `portfolio_monitoring_note`

### Evidence Requirements

- Must link to validated MarketEvents or direct evidence.
- Any affected segment or ticker must be explainable through those evidence links.

### Validation Rules

- `risk_type` and `status` must be controlled values.
- Risk changes must not become trade instructions.
- Every elevated risk must have either a relief condition, invalidation condition, or monitoring note.
- Risk regime updates cannot change deterministic risk constraints; they can only explain or trigger review.

### Consumed By Screens

- Daily Trading Cockpit
- AI Infrastructure Ecosystem Map
- Live Market / Sentiment Radar
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer

### LLM Analyst Role

- Create: `risk_regime_reviewer` for explanatory summaries.
- Review: `risk_regime_reviewer`.

### Deterministic Fields

- `regime_id`
- `risk_type`
- `status`
- `severity` when mapped from policy thresholds
- affected ticker and segment sets when rule-derived
- portfolio block flags
- constraint effects

## TradePlan

### Purpose

Represents an advisory, local-journal-oriented plan for reviewing possible manual action in one ticker.

### Fields

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

### Required Fields

- `trade_plan_id`
- `ticker`
- `company`
- `status`
- `advisory_action`
- `linked_event_ids`
- `linked_signal_bundle_id`
- `linked_recommendation_artifact_id`
- `readiness`
- `manual_journal_only`

### Evidence Requirements

- Must link to a recommendation artifact, signal bundle, and evidence-backed events.
- Entry, add, trim, exit, and invalidation levels must link to deterministic `EntryExitLevels`.
- Journal readiness must link to deterministic checks and stale-data status.

### Validation Rules

- `manual_journal_only` must be true.
- `status` must be one of draft, active, paused, invalidated, or retired.
- Any blocked plan must include `blocking_reasons`.
- No field may encode broker, order routing, execution, fill, or transmission state.
- A plan is not review-ready without evidence, risk checks, levels, and recommendation audit linkage.

### Consumed By Screens

- Daily Trading Cockpit
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: `trade_plan_critic` may draft plan narrative and local journal wording only.
- Review: `trade_plan_critic`.

### Deterministic Fields

- `status` when derived from readiness checks
- `advisory_action` after recommendation publication rules
- `linked_signal_bundle_id`
- `linked_recommendation_artifact_id`
- `entry_exit_levels_id`
- `price_target_scenario_id`
- `target_weights_id`
- `deterministic_check_ids`
- `readiness`
- `blocking_reasons` derived from missing checks

## PortfolioExposureSnapshot

### Purpose

Represents the deterministic portfolio state used by the workstation to show positions, segment exposure, correlation exposure, concentration, and PnL context.

### Fields

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

### Required Fields

- `snapshot_id`
- `as_of`
- `currency`
- `advisory_label`
- `total_market_value`
- `gross_equity_exposure`
- `position_count`
- `positions`

### Evidence Requirements

- Positions must come from portfolio facts or local journal-derived records.
- Prices, market values, weights, and PnL must link to market snapshots or deterministic portfolio calculations.
- Open trade plan links must resolve or be marked missing.

### Validation Rules

- `position_count` must equal the number of positions.
- Position weights must be deterministic and reconcile to the snapshot.
- PnL fields must be produced by deterministic calculation.
- Missing prices or stale prices must block balancing suggestions.
- Snapshot must not include broker account, order, routing, or execution fields.

### Consumed By Screens

- Daily Trading Cockpit
- AI Infrastructure Ecosystem Map
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: none for numeric exposure values.
- Review: `portfolio_exposure_explainer` may explain or critique supplied values.

### Deterministic Fields

- `total_market_value`
- `cash_placeholder`
- `gross_equity_exposure`
- `position_count`
- all position values
- `portfolio_weight`
- `unrealized_pnl`
- `correlation_exposure_ids`
- `pnl_summary_id`
- `target_weights_id`
- `concentration_flags`
- `stale_price_flags`

## AnalystBrief

### Purpose

Synthesizes the current daily analyst state into a cockpit-readable narrative and review queue.

### Fields

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

### Required Fields

- `brief_id`
- `as_of`
- `title`
- `advisory_label`
- `executive_summary`
- `highest_conviction_theme_updates`
- `ticker_focus_list`
- `open_questions`
- `next_review_triggers`

### Evidence Requirements

- Theme updates and ticker focus items must link to evidence-backed MarketEvents or downstream objects.
- Any suggested action must link to evidence, deterministic checks, or a trade plan.
- Brief must show stale or partial-data state if dependencies are incomplete.

### Validation Rules

- Advisory label must be visible.
- Brief cannot include execution language.
- Missing evidence or failed deterministic checks must reduce action readiness.
- LLM summary cannot modify deterministic rankings, scores, exposure, target weights, or PnL.

### Consumed By Screens

- Daily Trading Cockpit
- Live Market / Sentiment Radar
- Ticker Analyst Workbench
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: `brief_synthesizer`
- Review: `llm_note_reviewer`

### Deterministic Fields

- `brief_id`
- `as_of`
- `generated_at`
- `advisory_label`
- dependency object IDs
- freshness status
- blocked action flags
- ordering if generated from deterministic priority scores

## OutcomeJournalEntry

### Purpose

Captures local-only manual analyst records and outcome review for intended or completed manual trades.

### Fields

- `outcome_entry_id`
- `trade_entry_id`
- `ticker`
- `entry_type`
- `local_only`
- `linked_trade_plan_id`
- `advisory_label_at_time`
- `recorded_price`
- `recorded_quantity`
- `recorded_at`
- `evidence_available_ids`
- `market_event_ids_available_at_decision`
- `pnl_id`
- `realized_pnl`
- `unrealized_pnl`
- `plan_adherence_status`
- `outcome_label`
- `analyst_note`
- `llm_review_note_id`

### Required Fields

- `outcome_entry_id`
- `trade_entry_id`
- `ticker`
- `entry_type`
- `local_only`
- `linked_trade_plan_id`
- `recorded_at`
- `outcome_label`

### Evidence Requirements

- Must preserve evidence available at decision time.
- Completed manual trades should link to a trade plan or be marked unplanned.
- Outcome review must reference PnL summaries and relevant MarketEvents where available.

### Validation Rules

- `local_only` must be true.
- Journal entries must not transmit to any broker or external trading system.
- PnL fields must come from deterministic `PnLSummary`.
- Plan adherence must come from deterministic comparison against the trade plan and entry/exit levels.
- Missing linked plan must be visible as an unplanned/manual exception.

### Consumed By Screens

- Daily Trading Cockpit
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: `outcome_reviewer` may draft lessons and critique text.
- Review: `outcome_reviewer`.

### Deterministic Fields

- `pnl_id`
- `realized_pnl`
- `unrealized_pnl`
- `plan_adherence_status`
- evidence availability window
- position reconstruction linkage
- any outcome metric

## LLMAnalystNote

### Purpose

Stores a bounded LLM explanation, critique, summary, or review note tied to specific analyst objects.

### Fields

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

### Required Fields

- `note_id`
- `model_run_id`
- `scope`
- `allowed_role`
- `note`
- `deterministic_fields_not_modified`

### Evidence Requirements

- Notes that summarize claims must link to reviewed objects or evidence.
- Notes that critique trade plans must link to the relevant TradePlan and evidence-backed upstream objects.

### Validation Rules

- `allowed_role` must be controlled.
- Note text must not contain execution instructions.
- `deterministic_fields_not_modified` must list protected fields when the note discusses scores, risk, target weights, levels, exposure, or PnL.
- Every note must link to a `ModelRun`.

### Consumed By Screens

- Daily Trading Cockpit
- Live Market / Sentiment Radar
- Ticker Analyst Workbench
- Trade Plan + Entry/Exit Workbench
- Portfolio + Exposure Balancer
- Trade Journal + PnL Review

### LLM Analyst Role

- Create: role named in `allowed_role`.
- Review: `llm_note_reviewer`.

### Deterministic Fields

- `note_id`
- `model_run_id`
- `created_at`
- `allowed_role`
- `review_status`
- protected-field audit list

## Manual Validation Against Current Mock Data

Validated file: `docs/mock_data/situational_awareness_brief.example.json`

### Observed Shape

- Canonical-style fixture feeds: `source_signals`: 9 records, `market_events`: 9 records, `segment_impacts`: 8 records, `equity_impact_assessments`: 22 records, `financial_snapshots`: 22 records, `valuation_contexts`: 22 records, `risk_regime_updates`: 5 records.
- Advisory and audit feeds: `trading_advisories`: 7 records, `advisory_updates`: 4 records, `advisory_readiness_checks`: 8 records, `evidence_items`: 24 records, `model_runs`: 21 records, `signal_bundles`: 22 records, `target_weight_sets`: 1 record.
- Display-compatibility groups: `MarketEvents`: 5 records, `SegmentImpacts`: 6 records, `EquityImpactAssessments`: 10 records, `RiskRegimeUpdates`: 4 records, `AnalystBrief`: 1 object.
- Workstation feeds: `portfolio_snapshot`: 22-position summary, `open_trade_plans`: 7 plans, `price_target_scenarios`: 7 scenarios, `entry_exit_levels`: 7 level sets, `correlation_exposures`: 4 clusters, `llm_analyst_notes`: 3 notes.
- Data-control feeds: `freshness_metadata`: 1 object, `valuation_data_source_plan`: 5 source categories, `llm_analyst_roles`: 8 role definitions, `suppressed_advisory_candidates`: 3 candidates.

The fixture covers these portfolio and plan tickers: `AMD`, `AMZN`, `ANET`, `ASML`, `AVGO`, `CEG`, `DLR`, `EQIX`, `ETN`, `GOOGL`, `META`, `MRVL`, `MSFT`, `MU`, `NVDA`, `ORCL`, `PWR`, `TSM`, `VRT`. It also carries semicap evidence for `AMAT`, `LRCX`, and `KLAC`.

### Manual Validation Results

- JSON parses successfully.
- Segment, equity, risk, and trade-plan `linked_event_ids` resolve to existing `market_events`.
- Every top-position `linked_trade_plan_id` resolves to `open_trade_plans`.
- Every open trade plan ticker has matching `entry_exit_levels` and `price_target_scenarios`.
- Every `open_trade_plans[].manual_journal_only` value is `true`.
- Every `trading_advisories[].readiness_check_ids` reference resolves to `advisory_readiness_checks`.
- `AnalystBrief` now includes `generated_at`, `market_event_ids`, `segment_impact_ids`, `risk_regime_update_ids`, `suggested_action_ids`, `model_run_ids`, `readiness_check_ids`, `freshness_status`, stale-source context, suppressed count, and `last_successful_run_id`.
- `freshness_metadata` carries `as_of`, `generated_at`, `last_successful_run_id`, object-family freshness, stale-source notes, and suppressed reason counts.
- `valuation_data_source_plan` defines allowed public/configured source categories for financial snapshots, valuation context, macro context, and segment catalyst evidence.
- `llm_analyst_roles` defines source classification, catalyst extraction, segment mapping, equity thesis review, valuation narrative review, risk critique, brief synthesis, and outcome review boundaries.
- Current fixture uses advisory wording and does not contain broker, order-routing, or execution-state objects.

### Mismatches And Hardening Gaps

- The fixture includes first-class `evidence_items`, `model_runs`, `signal_bundles`, `target_weight_sets`, and `advisory_readiness_checks`, but still lacks first-class `EvidenceChunk`, `EvidenceClaim`, `RecommendationArtifact`, and deterministic check objects. It uses ID strings or summary lists for those references.
- `source_signals` remain fixture-shaped rather than full `SourceSignal` contract objects. They lack canonical `source_uri`, `publisher`, `captured_at`, `available_at`, `raw_summary`, `data_class`, `content_hash`, and one-to-one `evidence_id` fields.
- `SegmentImpact` records still lack explicit `first_order_tickers`, `second_order_tickers`, `confidence`, `time_horizon`, `latest_evidence_at`, and `model_run_ids`. The fixture uses `primary_tickers`, `derivative_tickers`, `risk_flags`, and `invalidation_condition` instead.
- `EquityImpactAssessment` records are closer to the model but still lack `as_of`, `available_at`, direct `source_evidence_ids`, and recommendation artifact links.
- `RiskRegimeUpdate` records lack `severity`, `confidence`, `affected_segments`, `affected_tickers`, `invalidation_condition`, `as_of`, `available_at`, and direct `source_evidence_ids`.
- `TradePlan` records are local-journal-safe, but they lack explicit `entry_exit_levels_id`, `price_target_scenario_id`, `target_weights_id`, `deterministic_check_ids`, and `last_reviewed_at`. The current fixture joins levels and scenarios by ticker instead.
- `portfolio_snapshot` is the fixture name for `PortfolioExposureSnapshot`. It carries aggregate exposure state but lacks per-position `last_price_timestamp`, explicit `correlation_exposure_ids`, `pnl_summary_id`, `target_weights_id`, `concentration_flags`, and `stale_price_flags`.
- `OutcomeJournalEntry` is not first-class in the fixture. The closest representation is `manual_trade_journal.entries` plus `trade_journal_summary`, which lacks full object-model fields such as `outcome_entry_id`, `recorded_price`, `recorded_quantity`, `recorded_at`, `evidence_available_ids`, `pnl_id`, `plan_adherence_status`, and `llm_review_note_id`.
- `LLMAnalystNote` records include `model_run_id`, `scope`, `allowed_role`, `evidence_ids`, `note`, and protected deterministic fields, but lack `reviewed_object_ids`, `created_at`, and `review_status`.

These gaps are acceptable for the current mock fixture as a rich UI prototype, but they should be resolved before the fixture is treated as a canonical schema contract or persistence payload.
