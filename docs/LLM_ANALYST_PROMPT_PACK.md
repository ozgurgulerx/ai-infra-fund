# LLM Analyst Prompt Pack

## Purpose

This pack defines bounded role prompts for the AI Infrastructure Trading Advisory Workstation. The roles support source monitoring, evidence interpretation, MarketEvent extraction, segment mapping review, thesis analysis, risk review, advisory narrative drafting, trade-plan critique, brief synthesis, and outcome review.

The pack is documentation only. It defines contracts for future prompt implementations and tests. It does not enable real model calls.

## Global Boundary

- The system is advisory-only.
- LLMs may classify, extract, summarize, review, critique, and explain.
- LLMs must not generate final deterministic scores, target weights, constraints, PnL, final entry or exit levels, correlation exposure, concentration checks, publication gates, or executable trade instructions.
- Deterministic code owns numeric scoring, risk, constraints, target weights, scenario values, entry and exit levels, portfolio exposure, PnL, and publication checks.
- All model routing must use `config/model_profiles.yaml`; prompts reference routing roles, not deployment names.
- Every model-assisted output must create or link to a `ModelRun` record.
- Every `ModelRun` must preserve role, prompt version, input hash, output hash, data class, schema validity, retry count, latency when available, and denial or fallback status when applicable.
- Cloud calls must pass data-class policy. private research is local-only by default.
- Prompt outputs must never contain brokerage, routing, trade-submission, fill, automated-market-action, or execution output.
- All material claims must cite evidence identifiers, source URIs, available timestamps, and content hashes when present.

## Routing Roles

Use these role names as routing intent. The router maps each role to an allowed profile in `config/model_profiles.yaml`:

- `source_classification`
- `evidence_summary`
- `orchestration_validation`
- `adversarial_review`
- `local_fallback`

If no allowed route is available for the input data class, return a denied/fallback result and write audit metadata. Do not silently continue with an ungoverned model.

## Shared Prompt Envelope

Every role prompt should include:

- role name and prompt version
- data class
- source evidence IDs
- source URIs
- available timestamps
- content hashes
- allowed output schema
- forbidden output list
- deterministic ownership reminder
- requested confidence bounds
- required review status
- fallback behavior

Every role response should include:

- role name
- prompt version
- `model_run_id` or pending audit placeholder
- input evidence IDs
- output object IDs
- schema validity flag
- confidence
- review status
- refusal or fallback reason when applicable

## Role: `source_signal_monitor`

### Allowed inputs

- Public or configured source metadata.
- Source URI, publisher, captured timestamp, available timestamp, content hash, data class, and evidence ID.
- Watchlist tickers, themes, segments, and source-registry metadata.

### Allowed outputs

- Draft `SourceSignal` summaries.
- Source type, ticker tags, theme tags, segment tags, data-class label, and confidence.
- Evidence-backed notes about why the source matters to the AI infrastructure analyst loop.

### Forbidden outputs

- Advisory labels.
- Deterministic scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Claims without evidence identifiers.

### Schema expectations

- Output must conform to `SourceSignal`.
- Required fields: `signal_id`, `source_type`, `source_uri`, `publisher`, `captured_at`, `available_at`, `raw_summary`, `data_class`, `content_hash`, `evidence_id`, and `confidence`.
- `confidence` must be bounded from 0.0 to 1.0.

### ModelRun audit requirements

- Use routing intent `source_classification` or `evidence_summary`.
- Record prompt version, input hash, output hash, data class, evidence IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If the source is private, unresolved, unsupported, or outside data-class policy, return a local-only or denied result.
- If the source lacks evidence linkage or content hash, mark the signal unusable for downstream advisory synthesis.

## Role: `market_event_extractor`

### Allowed inputs

- `EvidenceItem`, `EvidenceChunk`, `EvidenceClaim`, and `SourceSignal` objects.
- Watchlist tickers, segment map, theme map, source URI, available timestamp, and content hash.

### Allowed outputs

- Draft `MarketEvent` objects.
- Catalyst summary, event type, affected tickers, companies, themes, segments, direction, time horizon, confidence, and review status.
- Evidence references for every material event claim.

### Forbidden outputs

- Deterministic scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Events with no source evidence IDs.

### Schema expectations

- Output must conform to `MarketEvent`.
- Required fields: `event_id`, `event_type`, `source_evidence_ids`, `tickers`, `companies`, `themes`, `segments`, `catalyst`, `ai_relevance`, `direction`, `time_horizon`, `confidence`, `occurred_at`, `available_at`, `content_hash`, `extracted_by_model_run_id`, and `review_status`.
- `source_evidence_ids`, `available_at`, and `content_hash` are mandatory.

### ModelRun audit requirements

- Use routing intent `evidence_summary` for extraction and `orchestration_validation` for schema repair.
- Record extraction role, prompt version, input hash, output hash, event IDs, evidence IDs, data class, schema validity, retry count, and fallback status.

### Escalation and fallback

- If event type, timestamp, source evidence, or content hash is missing, output `review_status: needs_review`.
- If extraction is denied by data-class policy, return a denial artifact and let deterministic fallback keep the pipeline running without model-derived events.

## Role: `segment_mapping_reviewer`

### Allowed inputs

- Validated `MarketEvent` objects.
- Segment taxonomy, watchlist tickers, company map, theme map, and evidence IDs.
- Draft `SegmentImpact` objects produced by deterministic or reviewed workflows.

### Allowed outputs

- Review notes for `SegmentImpact`.
- First-order and second-order beneficiary or pressure mapping.
- Missing segment, ticker, contradiction, or stale-thesis flags.

### Forbidden outputs

- Deterministic impact scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Segment changes unsupported by evidence.

### Schema expectations

- Output must preserve or review `SegmentImpact`.
- Required review fields: segment, first-order tickers, second-order tickers, impact direction, evidence IDs, confidence, and review status.
- Any contradiction must reference the conflicting evidence IDs.

### ModelRun audit requirements

- Use routing intent `adversarial_review` for contradiction review or `orchestration_validation` for schema repair.
- Record prompt version, input hash, output hash, event IDs, segment impact IDs, evidence IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If a segment mapping is ambiguous, return competing hypotheses and mark the object `needs_review`.
- If evidence is stale or unresolved, block downstream readiness rather than creating a stronger thesis.

## Role: `equity_thesis_analyst`

### Allowed inputs

- Validated `MarketEvent`, `SegmentImpact`, `EvidenceClaim`, `FinancialSnapshot`, and `ValuationContext` objects.
- Current thesis map, stale-thesis markers, contradiction markers, risk flags, and watchlist metadata.

### Allowed outputs

- Narrative portions of `EquityImpactAssessment`.
- Bull case, bear case, risk flags, invalidation condition, thesis freshness notes, and evidence-backed ticker implications.
- Contradiction and missing-evidence flags.

### Forbidden outputs

- Final deterministic scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Unsupported buy/sell claims or generic market commentary without ticker implication.

### Schema expectations

- Output must conform to narrative fields of `EquityImpactAssessment`.
- Required evidence linkage: event IDs, segment impact IDs, evidence IDs, and model run IDs where model-assisted.
- Confidence must be bounded from 0.0 to 1.0.

### ModelRun audit requirements

- Use routing intent `evidence_summary` for thesis draft and `adversarial_review` for contradiction review.
- Record prompt version, input hash, output hash, ticker IDs, evidence IDs, review findings, schema validity, retry count, and fallback status.

### Escalation and fallback

- If bull and bear cases conflict without enough evidence, emit `needs_review`.
- If the data class disallows the planned route, return a denied/fallback result and preserve deterministic pipeline continuity.

## Role: `risk_regime_reviewer`

### Allowed inputs

- `MacroRegimeSnapshot`, `RiskRegimeUpdate`, `SystemicRiskEvent`, `MarketEvent`, evidence IDs, and deterministic risk flags.
- Rates, liquidity, semiconductor cycle, AI capex cycle, energy, geopolitical, and export-control context.

### Allowed outputs

- Narrative risk regime review.
- Relief conditions, worsening triggers, contradiction flags, missing-evidence flags, and advisory impact notes.

### Forbidden outputs

- Deterministic risk scores, constraints, target weights, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Risk changes without evidence IDs.

### Schema expectations

- Output must preserve deterministic risk values and only add review narrative or flags.
- Required links: evidence IDs, related event IDs, affected segments, affected tickers, and review status.

### ModelRun audit requirements

- Use routing intent `adversarial_review` or `evidence_summary`.
- Record prompt version, input hash, output hash, risk object IDs, evidence IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If systemic risk is material but evidence is incomplete, escalate to human review and prevent stronger advisory language.
- If the model route is unavailable, keep deterministic risk state and add a missing-review flag.

## Role: `trading_advisory_synthesizer`

### Allowed inputs

- Validated `MarketEvent`, `SegmentImpact`, `EquityImpactAssessment`, `ValuationContext`, `RiskRegimeUpdate`, `SignalBundle`, `TargetWeights`, and deterministic checks.
- Evidence IDs, model run IDs, target weights ID, signal bundle ID, and publication policy result.

### Allowed outputs

- Advisory-only narrative for `TradingAdvisory`.
- Watch, accumulate, hold, trim, avoid, or exit-candidate label explanation when the label was supplied by deterministic policy.
- Risk, invalidation, valuation, catalyst, and evidence summary.

### Forbidden outputs

- Final deterministic scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Advisory publication when required deterministic IDs or checks are missing.

### Schema expectations

- Output must conform to narrative fields of `TradingAdvisory`.
- Required references: advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID, deterministic checks, and advisory-only label.
- The role may explain entry, add, trim, exit, and invalidation planning levels only when deterministic inputs provide them.

### ModelRun audit requirements

- Use routing intent `evidence_summary` for synthesis and `orchestration_validation` for schema repair.
- Record prompt version, input hash, output hash, advisory ID, upstream object IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If any required deterministic ID or evidence link is missing, return a suppression explanation rather than an advisory.
- If language sounds executable, route to review and downgrade to planning-only wording.

## Role: `trade_plan_critic`

### Allowed inputs

- Advisory-only `TradingAdvisory`, deterministic trade plan fields, risk flags, invalidation levels, journal readiness checks, and local manual journal context.
- Evidence IDs and deterministic checks.

### Allowed outputs

- Critique notes for a local manual trade plan.
- Missing-evidence warnings, stale-level warnings, risk concentration warnings, and journal note drafts.
- Planning-only reminders.

### Forbidden outputs

- Deterministic scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Any instruction to transmit a market action.

### Schema expectations

- Output must be a critique note linked to advisory ID, evidence IDs, risk flags, invalidation condition, and review status.
- It must preserve deterministic levels and values without recalculation.

### ModelRun audit requirements

- Use routing intent `adversarial_review`.
- Record prompt version, input hash, output hash, advisory ID, evidence IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If the plan lacks invalidation, evidence, or deterministic readiness checks, mark it not review-ready.
- If private journal context is included, route local-only or deny cloud use under data-class policy.

## Role: `brief_synthesizer`

### Allowed inputs

- Validated SourceSignals, MarketEvents, SegmentImpacts, EquityImpactAssessments, RiskRegimeUpdates, TradingAdvisories, evidence IDs, and audit IDs.
- Deterministic ranking, risk, and readiness flags.

### Allowed outputs

- Daily or intraday analyst brief narrative.
- Top catalysts, affected tickers, theme propagation, evidence links, risk flags, invalidation conditions, confidence, and advisory label explanations.

### Forbidden outputs

- Final deterministic scores, target weights, constraints, PnL, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Broad market commentary without ticker-level implication.

### Schema expectations

- Output must conform to `AnalystBrief`.
- Every material statement must link to evidence IDs or upstream object IDs.
- Advisory labels must come from upstream advisory artifacts, not from the model.

### ModelRun audit requirements

- Use routing intent `evidence_summary`.
- Record prompt version, input hash, output hash, brief ID, upstream object IDs, evidence IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If there are no validated events, create an empty-state brief with missing-input notes.
- If evidence conflicts, surface contradiction flags rather than hiding them in prose.

## Role: `outcome_reviewer`

### Allowed inputs

- Local `OutcomeJournalEntry`, prior `TradingAdvisory`, MarketEvents, risk flags, deterministic PnL, deterministic exposure values, and evidence IDs.
- Analyst notes and manual journal records.

### Allowed outputs

- Outcome review narrative.
- Lessons learned, thesis-quality critique, evidence-quality critique, scenario replay notes, and proposed evaluation tags.

### Forbidden outputs

- Deterministic PnL, scores, target weights, constraints, final entry or exit levels, or executable trade instructions.
- Brokerage, routing, fill, automated-market-action, or execution output.
- Blame-free rewriting of the original thesis without point-in-time evidence.

### Schema expectations

- Output must conform to narrative fields of `OutcomeJournalEntry` or related outcome review notes.
- Required links: prior advisory ID, evidence IDs, journal ID, deterministic outcome fields, and review status.
- The role may critique but must not overwrite deterministic accounting values.

### ModelRun audit requirements

- Use routing intent `adversarial_review` or `evidence_summary`.
- Record prompt version, input hash, output hash, outcome ID, prior advisory ID, evidence IDs, schema validity, retry count, and fallback status.

### Escalation and fallback

- If private journal notes are included, route local-only or deny cloud use under data-class policy.
- If point-in-time evidence is missing, mark outcome review incomplete and request evidence repair.
