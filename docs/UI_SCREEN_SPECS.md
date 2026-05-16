# UI Screen Specs

## Product Frame

This document defines the implementation-ready UX shape for the AI Infrastructure Trading Analyst Workstation. The product is a daily trading cockpit for AI infrastructure equities: catalyst-driven, evidence-backed, portfolio-aware, and fast enough for daily review. It is not a generic market dashboard, passive daily newsletter, broker terminal, execution surface, or backtesting-first quant tool.

Primary workflow:

```text
Evidence -> MarketEvent -> SegmentImpact -> EquityImpactAssessment -> RiskRegimeUpdate -> SignalBundle -> RecommendationArtifact -> TradePlan -> ManualTradeJournal -> PnLReview
```

Daily workstation loop:

```text
Open Cockpit -> Check Radar -> Inspect Ecosystem Map -> Work Ticker -> Review Trade Plan -> Balance Exposure -> Journal Outcome
```

Primary screens:

| Screen | Workflow Role | Primary Output |
| --- | --- | --- |
| Daily Trading Cockpit | Daily triage and action queue | Review priorities and blocked actions |
| AI Infrastructure Ecosystem Map | Segment and theme propagation | First-order and second-order ticker implications |
| Live Market / Sentiment Radar | Intraday catalyst and sentiment monitoring | Validated alerts for analyst review |
| Ticker Analyst Workbench | Single-name thesis and setup analysis | Evidence-backed ticker assessment |
| Trade Plan + Entry/Exit Workbench | Advisory plan readiness | Local-only trade plan and journal readiness |
| Portfolio + Exposure Balancer | Portfolio context and constraint review | Advisory balancing review list |
| Trade Journal + PnL Review | Outcome learning loop | Deterministic PnL review and analyst lessons |

Global rules:

- Advisory-only.
- No broker integration.
- No live order placement.
- No execution UI.
- No order tickets, submit buttons, route controls, fill simulation controls, or broker account views.
- Manual trade entry is local journal only and must not transmit to any broker, venue, exchange, or trading API.
- Recommendation language must remain advisory-only: watch, accumulate, hold, trim, avoid, exit-candidate.
- LLMs may classify, extract, summarize, review, critique, and explain.
- LLMs must not own final scores, risk, constraints, target weights, or PnL calculations.
- Deterministic code owns scores, risk, constraints, target weights, concentration checks, correlation checks, exposure calculations, and PnL calculations.
- Every recommendation-like label must link to evidence, signal bundles, deterministic checks, and audit records where available.
- UI must render API/domain objects only; it must not compute portfolio weights, scores, risk limits, PnL, or target weights.
- Entry, exit, add, trim, and invalidation language describes advisory plan conditions only; it must never become an order ticket, routing instruction, or execution workflow.
- Trade journal writes are local analyst records for intended or completed manual trades; they must not transmit anything to external trading systems.

## 1. Daily Trading Cockpit

### User Question

What should I review before making any manual AI infrastructure trading decisions today, what changed, which names need action, and what risks block action?

### Primary Decisions Supported

- Decide which tickers require immediate analyst review.
- Decide whether an existing trade plan should be kept, revised, paused, or invalidated.
- Decide whether a manual journal entry is needed for an intended or completed trade.
- Decide which alerts, catalysts, and risk changes deserve deeper workbench review.

### Required Data Objects

- `AnalystBrief`
- `MarketEvent`
- `SegmentImpact`
- `EquityImpactAssessment`
- `RiskRegimeUpdate`
- `SignalBundle`
- `RecommendationArtifact`
- `TradePlan`
- `PortfolioSnapshot`
- `WatchlistAlert`
- `TradeJournal`
- `PnLSummary`
- `EvidenceItem`
- `ModelRun`

### Sections

- Header: trading date, as_of timestamp, latest data freshness, advisory-only label, latest successful run id.
- Action queue: suggested research actions, blocked actions, stale actions, and review-needed items.
- Catalyst tape: AI infrastructure catalysts by urgency and evidence freshness.
- Position impact: current holdings and watchlist names affected by catalysts.
- Open trade plans: planned entries, exits, trims, adds, invalidation status, and manual-journal readiness.
- Risk regime strip: power, HBM, CoWoS, export-control, capex, datacenter, and market-liquidity risk changes.
- PnL and exposure snapshot: deterministic daily and cumulative PnL, concentration, segment, and correlation exposure.
- LLM analyst notes: critique and explanation only, clearly separated from deterministic signals.
- Ops/audit footer: stale data, failed runs, missing evidence, and model run links.

### Card/Table Fields

- Ticker.
- Company.
- Current advisory label.
- Position weight.
- Open trade plan status.
- Latest catalyst.
- Catalyst type.
- Impact direction.
- Signal score id.
- Deterministic risk flags.
- Entry zone.
- Exit or trim zone.
- Invalidation level or condition.
- Price target scenario ids.
- Evidence ids and links.
- Model run ids.
- Freshness timestamp.
- Suggested next analyst action.

### Proactive LLM Suggestions

- Summarize what changed since the last completed cockpit run.
- Explain why a trade plan is blocked by risk, evidence, or stale data.
- Critique whether a thesis has become over-dependent on one catalyst.
- Draft analyst notes for the local trade journal, without producing an order instruction.
- Highlight contradictions between MarketEvents, evidence claims, and existing trade plans.

### Empty, Loading, And Error States

- Empty: no completed cockpit run for the selected date; show latest available brief and mark the day as not ready.
- Loading: show stage-level progress for evidence ingestion, event extraction, deterministic signals, portfolio checks, and brief generation.
- Error: show failed dependency, run id, stale-data warning, and affected sections.
- Partial: render available sections but suppress action urgency when signals, risk checks, or evidence links are missing.

### Acceptance Criteria

- Advisory-only label is visible above all recommendation-like labels.
- The primary screen shows daily trading workflow objects, not generic market widgets.
- Every suggested action links to evidence, deterministic checks, or a trade plan.
- No order, broker, execution, submit, route, or fill controls appear.
- Manual trade entry is framed as local journal capture only.
- Deterministic fields are labeled as system-computed, not LLM-computed.
- Stale or missing evidence visibly blocks action readiness.

### Out Of Scope

- Order entry.
- Broker status.
- Live execution controls.
- Generic index dashboard.
- Backtest optimizer as the main experience.
- UI-side scoring or portfolio calculations.

## 2. AI Infrastructure Ecosystem Map

### User Question

Where is the AI infrastructure stack accelerating, constrained, weakening, or exposed to risk, and which equities are first-order or second-order beneficiaries?

### Primary Decisions Supported

- Decide which AI infrastructure segments deserve capital attention.
- Decide whether a ticker is a first-order or derivative exposure to a catalyst.
- Decide whether a thesis is becoming crowded, stale, contradicted, or capacity-constrained.
- Decide where to look for new trade plans or invalidations.

### Required Data Objects

- `Segment`
- `SegmentImpact`
- `MarketEvent`
- `EquityImpactAssessment`
- `RiskRegimeUpdate`
- `EvidenceClaim`
- `RecommendationArtifact`
- `PortfolioSnapshot`

### Sections

- Ecosystem stack map: model progress, hyperscaler capex, accelerators, HBM, CoWoS, foundry/equipment, networking, datacenters, power/grid, cooling/electrical, sovereign/export controls, and software monetization.
- Segment detail panel: selected segment state, latest catalysts, constraints, beneficiaries, and losers.
- Exposure overlay: current portfolio exposure and watchlist exposure by segment.
- Bottleneck tracker: HBM, CoWoS, substrates, power, interconnection, and datacenter capacity.
- Policy and sovereign AI panel: export-control changes and national AI infrastructure signals.
- Evidence and contradiction panel: source claims, stale-thesis markers, and unresolved contradictions.

### Card/Table Fields

- Segment name.
- Segment state: accelerating, stable, deteriorating, constrained, policy-risk, unknown.
- Latest catalyst.
- Event count.
- First-order tickers.
- Second-order tickers.
- Portfolio exposure.
- Watchlist exposure.
- Deterministic segment signal id.
- Risk flags.
- Invalidation condition.
- Latest evidence timestamp.
- Evidence ids and links.
- Contradiction count.
- Stale-thesis marker.

### Proactive LLM Suggestions

- Explain why a segment moved and which evidence supports the change.
- Identify tickers that appear under-covered relative to segment momentum.
- Summarize contradictions between segment demand and supply constraints.
- Suggest analyst questions for the ticker workbench.
- Flag when the ecosystem map is leaning on stale evidence.

### Empty, Loading, And Error States

- Empty: no segment impacts exist; prompt for validated MarketEvents with segment mappings.
- Loading: show canonical segment skeletons and latest run timestamp.
- Error: distinguish missing segment mapping, evidence API failure, and stale signal bundle.
- Partial: render mapped segments and mark unmapped events as review-needed.

### Acceptance Criteria

- Segment states are driven by `SegmentImpact` and deterministic signal objects, not UI calculations.
- First-order and second-order tickers are visually distinct.
- Every segment movement links to at least one evidence-backed MarketEvent.
- Portfolio exposure is shown only from provided `PortfolioSnapshot` data.
- No generic sector screener or ETF browser appears.

### Out Of Scope

- Arbitrary sector browsing.
- Drag-and-drop graph editing.
- Manual segment scoring in the UI.
- Broker or execution controls.
- Backtest-first factor exploration.

## 3. Live Market / Sentiment Radar

### User Question

What live market, news, sentiment, and catalyst signals are moving AI infrastructure equities today, and which ones are actionable for analyst review?

### Primary Decisions Supported

- Decide whether a move is catalyst-backed or noise.
- Decide which watchlist alerts should become ticker workbench reviews.
- Decide whether an open trade plan should be paused due to volatility, sentiment reversal, or stale evidence.
- Decide which evidence items need validation before influencing recommendations.

### Required Data Objects

- `MarketSnapshot`
- `WatchlistAlert`
- `MarketEvent`
- `EvidenceItem`
- `EvidenceClaim`
- `SentimentSnapshot`
- `SignalBundle`
- `RiskRegimeUpdate`
- `ModelRun`

### Sections

- Radar header: market timestamp, source freshness, advisory-only label, data-quality status.
- AI infrastructure movers: ticker moves, volume anomalies, and catalyst linkage.
- Sentiment tape: source-classified sentiment from filings, earnings calls, reputable news, analyst notes, and selected public channels.
- Event validation queue: new, pending, usable, rejected, quarantined, and stale events.
- Alert stream: price, volume, catalyst, thesis, risk, and evidence alerts.
- Evidence detail drawer: source, claim, content hash, extracted spans, and model run ids.
- Volatility and breadth context: deterministic market context for interpreting alerts.

### Card/Table Fields

- Alert id.
- Ticker.
- Company.
- Alert type.
- Price change.
- Volume change.
- Sentiment direction.
- Catalyst link.
- MarketEvent id.
- Evidence ids and links.
- Signal bundle id.
- Risk flags.
- Data freshness.
- Review status.
- Suggested analyst next step.

### Proactive LLM Suggestions

- Classify whether an alert appears catalyst-backed, sentiment-only, or data-noise.
- Summarize the evidence behind a market move.
- Flag events whose language implies trade action and rewrite them as advisory research notes.
- Compare today's sentiment to the current thesis without changing deterministic scores.
- Suggest which alerts should be escalated to the ticker workbench.

### Empty, Loading, And Error States

- Empty: no watchlist alerts or market snapshots for the selected window.
- Loading: show source-by-source loading state and latest available snapshot.
- Error: distinguish market data failure, evidence ingestion failure, sentiment extraction failure, and stale run state.
- Partial: show available alerts but mark downstream action readiness unavailable when evidence or signal bundles are missing.

### Acceptance Criteria

- Radar is restricted to AI infrastructure watchlist and portfolio names.
- Market moves without catalyst evidence are labeled as unconfirmed.
- LLM sentiment is clearly separated from deterministic market data.
- Alerts cannot imply automatic trading action.
- No live order, quote-to-trade, route, or execution controls appear.

### Out Of Scope

- Generic full-market heatmap.
- Day-trading execution ladder.
- Options chain trading.
- Broker positions or account balances.
- UI-side sentiment scoring.

## 4. Ticker Analyst Workbench

### User Question

For this AI infrastructure ticker, what is the current evidence-backed thesis, what changed, what are the entry and exit considerations, and what would invalidate the plan?

### Primary Decisions Supported

- Decide whether the ticker deserves watch, accumulate, hold, trim, avoid, or exit-candidate status.
- Decide whether to create, revise, pause, or retire a local trade plan.
- Decide which evidence, risks, or price levels need review before any manual action.
- Decide whether the ticker belongs in the portfolio, watchlist, or no-action queue.

### Required Data Objects

- `EquityImpactAssessment`
- `MarketEvent`
- `SegmentImpact`
- `RiskRegimeUpdate`
- `SignalBundle`
- `RecommendationArtifact`
- `TradePlan`
- `PriceTargetScenario`
- `EntryExitLevels`
- `EvidenceClaim`
- `PortfolioSnapshot`
- `TradeJournal`

### Sections

- Ticker header: ticker, company, latest price snapshot, advisory-only label, assessment freshness.
- Thesis state: current thesis, thesis age, evidence coverage, contradiction count.
- Catalyst timeline: relevant MarketEvents and their availability timestamps.
- Segment exposure: first-order and second-order AI infrastructure segment mapping.
- Bull/base/bear scenarios: price target scenarios and assumptions.
- Entry/exit panel: deterministic entry zones, trim zones, stop/invalidation conditions, and stale-level warnings.
- Risk and invalidation panel: risk flags, relief conditions, and blocked-plan reasons.
- Evidence binder: evidence claims, source links, model runs, and audit details.
- Journal history: intended trades, completed manual trades, notes, and outcome labels.

### Card/Table Fields

- Ticker.
- Company.
- Segment exposures.
- Latest catalyst.
- Advisory label.
- Signal bundle id.
- Recommendation artifact id.
- Current position weight.
- Entry zone.
- Add zone.
- Trim zone.
- Exit-candidate condition.
- Invalidation condition.
- Bull target.
- Base target.
- Bear target.
- Risk flags.
- Evidence ids and links.
- Latest journal note.

### Proactive LLM Suggestions

- Summarize the ticker thesis in a bull/base/bear frame.
- Critique the trade plan for missing evidence, stale assumptions, or unhandled risks.
- Explain why a price level is an entry, add, trim, or invalidation level based on supplied deterministic objects.
- Draft local journal notes for analyst review.
- Identify contradictions between the latest catalyst and the existing thesis.

### Empty, Loading, And Error States

- Empty: ticker is in the universe but has no current `EquityImpactAssessment`.
- Loading: show ticker shell with last successful assessment timestamp.
- Error: distinguish missing ticker, missing evidence, stale signal bundle, failed price snapshot, and unavailable trade plan.
- Partial: show catalyst and evidence data but mark thesis incomplete until risk, invalidation, and scenario objects exist.

### Acceptance Criteria

- Bull, base, bear, risk, and invalidation sections are present before a ticker assessment is complete.
- Entry/exit levels come from provided `EntryExitLevels`, not UI calculations.
- LLM notes are labeled as critique/explanation, not deterministic output.
- Every thesis claim links to evidence.
- No order-entry, execution, or broker controls appear.

### Out Of Scope

- Generic company profile terminal.
- Options strategy builder.
- Broker margin or account views.
- UI-side target generation.
- Automated trade submission.

## 5. Trade Plan + Entry/Exit Workbench

### User Question

What is the advisory trade plan for this ticker, what levels and conditions govern manual action, and what must be true before I record anything in the local journal?

### Primary Decisions Supported

- Decide whether to draft, update, pause, invalidate, or retire a trade plan.
- Decide whether a manual intended-trade journal entry is ready to record locally.
- Decide whether risk constraints, concentration, correlation, or stale evidence block action.
- Decide which entry, add, trim, exit, and invalidation levels need review.

### Required Data Objects

- `TradePlan`
- `EntryExitLevels`
- `PriceTargetScenario`
- `RecommendationArtifact`
- `SignalBundle`
- `TargetWeights`
- `ImplementationEstimate`
- `PortfolioSnapshot`
- `RiskRegimeUpdate`
- `EvidenceItem`
- `TradeEntry`

### Sections

- Plan header: ticker, plan id, status, advisory label, latest validation timestamp.
- Plan thesis: why the plan exists and which catalysts support it.
- Entry/add/trim/exit matrix: deterministic levels, conditions, and time horizon.
- Readiness checklist: evidence, risk, concentration, correlation, target-weight, and stale-data checks.
- Position sizing context: current weight, target-weight suggestion, max allowed exposure, and cash impact, all rendered from deterministic objects.
- Scenario panel: bull/base/bear upside/downside and invalidation path.
- Manual journal draft: local-only intended-trade or completed-trade note fields.
- Audit panel: evidence, signal bundle, recommendation artifact, target weights, model runs, and deterministic checks.

### Card/Table Fields

- Plan id.
- Ticker.
- Plan status: draft, active, paused, invalidated, retired.
- Advisory action label.
- Entry zone.
- Add zone.
- Trim zone.
- Exit zone.
- Invalidation level.
- Invalidation condition.
- Target weight suggestion id.
- Current weight.
- Max allowed weight.
- Correlation exposure flag.
- Concentration flag.
- Liquidity flag.
- Evidence status.
- Journal readiness.
- Last reviewed at.

### Proactive LLM Suggestions

- Critique whether the plan is internally consistent with the latest evidence.
- Explain blocked readiness items in plain language.
- Suggest journal wording for an intended manual trade.
- Compare the plan against the current risk regime.
- Flag when the plan uses stale levels or stale thesis assumptions.

### Empty, Loading, And Error States

- Empty: no trade plan exists; show requirements for creating an advisory plan from validated ticker assessment data.
- Loading: show plan skeleton and latest successful validation timestamp.
- Error: distinguish missing levels, missing recommendation artifact, failed target-weight check, stale evidence, and portfolio snapshot mismatch.
- Partial: show plan thesis but mark journal readiness unavailable until deterministic checks are present.

### Acceptance Criteria

- Trade plan language is advisory and local-journal-oriented.
- Manual entry fields are labeled local journal only.
- No submit, place order, execute, route, transmit, fill, or broker wording appears.
- Entry/exit levels and target weights are rendered from deterministic objects.
- Journal readiness is blocked when evidence, risk, or constraints are missing.
- Every plan links to evidence and audit ids.

### Out Of Scope

- Live order ticket.
- Broker API connection.
- Execution simulator.
- Broker cash or margin controls.
- LLM-generated sizing or levels.

## 6. Portfolio + Exposure Balancer

### User Question

How is the AI infrastructure portfolio exposed today, where are concentration and correlation risks, and what advisory balancing changes should I review manually?

### Primary Decisions Supported

- Decide whether exposure is too concentrated by ticker, segment, supplier bottleneck, customer, geography, or risk regime.
- Decide whether a suggested target-weight change deserves trade-plan review.
- Decide whether a planned add or trim is blocked by portfolio constraints.
- Decide which holdings should move to watch, hold, trim, or exit-candidate review.

### Required Data Objects

- `PortfolioSnapshot`
- `Position`
- `TargetWeights`
- `SignalBundle`
- `RecommendationArtifact`
- `CorrelationExposure`
- `RiskRegimeUpdate`
- `PnLSummary`
- `TradePlan`
- `TradeJournal`

### Sections

- Portfolio header: as_of, total market value, cash placeholder if available, advisory-only label, deterministic calculation timestamp.
- Segment exposure: accelerators, HBM, CoWoS, semicap, networking, datacenter REITs, power/grid, cloud platforms, and policy exposure.
- Concentration table: ticker weights, top exposures, max allowed weights, and breach flags.
- Correlation map: shared drivers such as hyperscaler capex, HBM supply, CoWoS, power availability, and export controls.
- Target-weight comparison: current weights versus deterministic target-weight suggestions.
- Suggested review actions: adds, trims, holds, pauses, and exit-candidate reviews.
- PnL context: realized, unrealized, daily, and thesis-bucket PnL from provided summaries.
- Blockers: stale prices, missing positions, failed risk checks, or incomplete target-weight artifacts.

### Card/Table Fields

- Ticker.
- Company.
- Current market value.
- Current weight.
- Target weight.
- Weight delta.
- Segment exposures.
- Correlation cluster.
- Concentration flag.
- Risk regime flags.
- Open trade plan id.
- Suggested review action.
- Deterministic check ids.
- PnL contribution.
- Last price timestamp.

### Proactive LLM Suggestions

- Explain which exposure clusters drive the portfolio's current risk.
- Summarize why a balancing suggestion exists, using deterministic output ids.
- Critique whether the portfolio is over-dependent on one AI infrastructure bottleneck.
- Flag suggested actions that conflict with current risk regimes or stale evidence.
- Draft review notes for the analyst, without changing target weights.

### Empty, Loading, And Error States

- Empty: no portfolio snapshot exists; show that exposure balancing cannot run without positions.
- Loading: show latest known snapshot and pending deterministic check stages.
- Error: distinguish stale prices, missing positions, failed target-weight generation, and unavailable correlation exposures.
- Partial: show positions but hide balancing recommendations until deterministic target weights and correlation exposures are present.

### Acceptance Criteria

- Exposure and PnL values are rendered from deterministic objects only.
- Suggested balancing actions link to target-weight and risk-check artifacts.
- Correlation exposure is tied to AI infrastructure drivers, not generic factor labels only.
- No broker account, rebalance submit, or execution controls appear.
- Manual follow-up routes into trade plans and local journal only.

### Out Of Scope

- Broker portfolio sync.
- Automated rebalancing.
- Execution cost optimizer as primary UX.
- UI-side risk or PnL calculations.
- Generic asset-allocation dashboard.

## 7. Trade Journal + PnL Review

### User Question

What manual trade decisions were recorded, how did they perform, which theses were right or wrong, and what should improve in the next trading cycle?

### Primary Decisions Supported

- Decide whether a past manual trade followed its advisory plan.
- Decide whether a thesis outcome strengthens, weakens, or invalidates future trade plans.
- Decide which PnL drivers came from catalysts, exposure, timing, or risk regime changes.
- Decide what lessons should be carried into the next analyst cycle.

### Required Data Objects

- `TradeJournal`
- `TradeEntry`
- `TradePlan`
- `Position`
- `PnLSummary`
- `OutcomeJournal`
- `RecommendationArtifact`
- `SignalBundle`
- `EvidenceItem`
- `MarketEvent`

### Sections

- Journal header: selected period, advisory-only label, local-only journal label, latest PnL calculation timestamp.
- Manual trade entries: intended trades, completed manual trades, edits, notes, and outcome status.
- Plan adherence: planned versus recorded entry/exit, invalidation adherence, and notes.
- PnL summary: realized, unrealized, daily, period-to-date, and thesis-bucket PnL from deterministic calculations.
- Attribution review: catalyst, segment, ticker, and risk-regime attribution where available.
- Lessons learned: analyst notes, LLM critique, and follow-up actions.
- Evidence replay: events and evidence that existed before each recorded decision.
- Export/review controls: local report generation only, with no broker transmission.

### Card/Table Fields

- Trade entry id.
- Ticker.
- Entry type: intended, completed_manual, note, correction.
- Local-only status.
- Linked trade plan id.
- Advisory label at time of entry.
- Recorded price.
- Recorded quantity.
- Recorded timestamp.
- Deterministic PnL id.
- Realized PnL.
- Unrealized PnL.
- Plan adherence status.
- Outcome label.
- Evidence ids available at decision time.
- Analyst note.

### Proactive LLM Suggestions

- Summarize why a trade worked or failed using journal, evidence, and PnL objects.
- Critique whether the manual decision followed the trade plan.
- Identify repeated failure modes such as late entries, ignored invalidations, or stale evidence.
- Draft lessons learned for the outcome journal.
- Compare the decision-time evidence set with later evidence without hindsight bias.

### Empty, Loading, And Error States

- Empty: no local journal entries for the selected period; show prompt to review open trade plans, not to place trades.
- Loading: show latest journal and PnL calculation timestamps.
- Error: distinguish journal API failure, PnL calculation unavailable, missing linked trade plan, and stale price data.
- Partial: show journal entries but mark PnL and attribution unavailable until deterministic calculations are present.

### Acceptance Criteria

- Journal screens are explicitly local-only and advisory-only.
- PnL is read from deterministic `PnLSummary` objects.
- Every completed manual trade can link back to a trade plan or be marked as unplanned.
- Outcome review shows evidence available at decision time.
- No broker upload, transmit, sync, order, route, or execution controls appear.
- LLM critique never rewrites PnL, risk, or target-weight calculations.

### Out Of Scope

- Tax-lot accounting as a primary workflow.
- Broker reconciliation.
- Automated execution review.
- Live fills or order status.
- UI-side PnL calculation.
