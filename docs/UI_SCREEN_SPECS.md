# UI Screen Specs

## Product Frame

This document defines the UX shape for the AI Infrastructure Trading Advisory Workstation. The product is used daily to monitor AI infrastructure sources, assess catalysts, update equity theses, review valuation scenarios, prepare manual trade plans, record local journal entries, and review outcomes.

The workstation is advisory and reporting-only. It is not a broker terminal, live trading system, order management system, execution blotter, or automated trading loop.

Primary workstation loop:

```text
Source Monitoring
-> Evidence Quality Review
-> Catalyst Detection
-> Segment Impact Mapping
-> Ticker Thesis Review
-> Valuation Scenario Review
-> Risk Regime Review
-> Trade Plan Review
-> Manual Journal Entry
-> Outcome Review
```

Primary screens:

1. Daily Trading Cockpit
2. Live Source Monitoring / Sentiment Radar
3. AI Infrastructure Segment Map
4. Ticker Analyst Workbench
5. Valuation & Price Target Workbench
6. Trade Plan Workbench
7. Portfolio Exposure Balancer
8. Manual Trade Journal + PnL Review
9. Advisory Update History
10. Evidence Library

## Hard Boundaries

- No broker integration.
- No live trading.
- No execution UI.
- No automated trading.
- No order routing.
- No broker credentials.
- Manual journal only.
- All advisory insights cite evidence.
- Price targets are scenarios, not promises or executable instructions.
- Entry and exit levels are trade-planning guidance only.
- LLMs may classify, extract, summarize, review, critique, and explain.
- Deterministic code owns scores, risk, constraints, target weights, portfolio exposure, PnL, scenario math, and data quality gates.
- UI must render supplied objects and status only; it must not compute scores, risk, PnL, target weights, or execution decisions.

## Shared Acceptance Criteria

- Every screen displays advisory/reporting-only context when showing recommendation-like content.
- Every recommendation-like insight links to evidence ids or clearly states that evidence is unavailable and suppresses action readiness.
- Every price target is labeled as a scenario.
- Every entry/exit level is labeled as trade-planning guidance only.
- Every manual trade control is framed as local journal capture only.
- No screen includes broker connection, order submission, order routing, live trading, execution controls, or automated trading loops.

## Workstation UX Contract

The UI should feel like a dense daily analyst workstation for manual trading decisions, not a consumer portfolio app, automated trading console, or broker overlay. Screens should favor sortable tables, compact review queues, evidence drawers, audit trails, and deterministic status strips over promotional panels or high-level marketing copy.

Global navigation should support the daily decision loop:

1. Start in the Daily Trading Cockpit.
2. Inspect new source and sentiment changes.
3. Map catalysts to infrastructure segments.
4. Review affected tickers.
5. Check valuation scenarios.
6. Review manual trade-plan guidance.
7. Check portfolio exposure constraints.
8. Record or review local journal outcomes.
9. Audit advisory changes.
10. Drill into evidence provenance.

Global UI rules:

- Use "Review", "Inspect", "Open workbench", "Add journal note", and "Mark reviewed" language.
- Do not use "Buy", "Sell", "Submit", "Route", "Execute", "Place order", "Connect broker", or "Auto-trade" commands.
- Any action-oriented label must resolve to review, local annotation, or local journal capture only.
- Recommendation-like summaries must expose evidence ids, model run ids, deterministic gate status, and stale-data warnings near the summary, not hidden in a secondary page.
- Price targets must be presented as scenario rows with assumptions, evidence, horizon, and invalidation, never as a single authoritative number.
- Entry, trim, and exit levels must be presented as advisory planning levels and require the user to make any real-world trading decision outside the product.
- Empty states should explain which upstream advisory data is missing; they should not invite broker connection or live market execution setup.
- Error states should fail closed by suppressing readiness labels when evidence, valuation, risk, or portfolio constraints cannot be validated.

## 1. Daily Trading Cockpit

### User Question

What changed since the last review, which AI infrastructure names need attention today, and what manual trading decisions should I prepare or avoid?

### Primary Decision Supported

Prioritize the daily review queue: hold current thesis, inspect a ticker, revise a trade plan, pause an advisory, update a local journal entry, or investigate missing evidence.

### Primary Data Objects

- `AnalystBrief`
- `MarketEvent`
- `SegmentImpact`
- `EquityImpactAssessment`
- `ValuationContext`
- `RiskRegimeUpdate`
- `TradePlan`
- `PortfolioExposureSnapshot`
- `RecommendationArtifact`
- `EvidenceItem`
- `ModelRun`
- `RunArtifact`

### Sections

- Run header: date, as_of timestamp, latest run id, freshness status, advisory-only label.
- Priority queue: tickers and segments requiring review.
- Manual decision checklist: items to inspect before any outside-the-system trading decision.
- Catalyst tape: high-impact events and evidence links.
- Position impact: affected holdings and watchlist names.
- Trade-plan readiness: plans ready, blocked, stale, invalidated, or journal-needed.
- Risk regime strip: macro liquidity, power, HBM, CoWoS, export-control, datacenter, and capex risk.
- Daily brief: executive summary, thesis deltas, contradictions, and follow-up questions.
- Audit footer: model run ids, evidence ids, data-quality warnings, failed run links.

### Card/Table Fields

- Ticker
- Company
- Current advisory label
- Review priority
- Latest catalyst
- Impact direction
- Segment exposure
- Position weight
- Trade plan status
- Entry scenario id
- Exit/trim scenario id
- Invalidation condition
- Risk flags
- Evidence ids
- Model run ids
- Last updated
- Next analyst action

### LLM-Generated Elements

- What changed since last run.
- Catalyst summary.
- Thesis contradiction summary.
- Risk narrative.
- Suggested analyst questions.
- Draft journal note text.

### Deterministic Elements

- Data freshness.
- Portfolio exposure.
- Position weights.
- Risk flags.
- Trade-plan status.
- Staleness checks.
- Recommendation suppression.
- PnL summary references.
- Evidence/model-run linkage validation.

### Empty/Loading/Error State

- Empty: show no completed cockpit run and link to source monitoring/evidence library.
- Loading: show pipeline stages for sources, evidence, catalysts, signals, portfolio checks, and brief assembly.
- Error: show failed run id, dependency, stale data scope, and suppressed sections.

### Acceptance Criteria

- The screen opens directly into a daily advisory workflow, not a marketing page.
- Each priority item cites evidence or is marked evidence-missing.
- Blocked trade plans show the blocking reason.
- Decision checklist actions navigate to review workbenches or local journal capture only.
- No order, broker, route, fill, execution, or live-trading controls appear.

### Out Of Scope

- Order entry.
- Broker account state.
- Live execution status.
- Automated trading triggers.
- Generic market dashboard widgets unrelated to AI infrastructure.

## 2. Live Source Monitoring / Sentiment Radar

### User Question

Which sources, news, filings, transcripts, analyst notes, and public signals are changing sentiment or catalyst quality for AI infrastructure equities?

### Primary Decision Supported

Decide whether a new source item should become usable evidence, a quarantined item, a catalyst candidate, or a ticker workbench review.

### Primary Data Objects

- `SourceItem`
- `EvidenceItem`
- `EvidenceClaim`
- `MarketEvent`
- `SentimentSnapshot`
- `WatchlistAlert`
- `DataQualityCheck`
- `ModelRun`

### Sections

- Source health: feeds, adapters, freshness, failures, and license/data-class status.
- Sentiment radar: source-classified positive, negative, mixed, and neutral signals.
- Catalyst candidates: unreviewed items with possible ticker/segment impact.
- Evidence validation queue: usable, rejected, stale, duplicate, and quarantined items.
- Alert tape: ticker, segment, volume, price, thesis, and risk alerts.
- Source detail drawer: source URI, content hash, extracted spans, claims, and model run ids.

### Card/Table Fields

- Source name
- Source type
- URI
- License label
- Data class
- Ticker/theme
- Sentiment direction
- Confidence
- Catalyst candidate type
- Review status
- Content hash
- Evidence id
- Claim ids
- Model run ids
- First seen
- Available at

### LLM-Generated Elements

- Source classification.
- Sentiment summary.
- Claim extraction.
- Duplicate explanation.
- Catalyst candidate rationale.
- Analyst review questions.

### Deterministic Elements

- Content hashing.
- Deduplication hashes.
- Freshness and availability timestamps.
- Data-class policy checks.
- Quarantine status.
- Required provenance validation.

### Empty/Loading/Error State

- Empty: no active source items; show configured source adapters and next scheduled/manual scan.
- Loading: show per-source fetch and parsing progress.
- Error: show failed adapter, policy denial, malformed source, or missing provenance.

### Acceptance Criteria

- Private research is clearly marked local-only.
- Every promoted catalyst candidate links to evidence and source metadata.
- Sentiment is advisory context only and does not become an order signal.
- Quarantined evidence cannot appear as usable advisory support.

### Out Of Scope

- Scraping private paid reports into committed files.
- Unlicensed content redistribution.
- Cloud model calls for private research unless explicitly policy-approved and audited.
- Broker/trading actions.

## 3. AI Infrastructure Segment Map

### User Question

Which parts of the AI infrastructure stack are accelerating, constrained, deteriorating, or exposed to risk, and which equities are affected first or second order?

### Primary Decision Supported

Decide which segments deserve research attention and which tickers need thesis updates or trade-plan review.

### Primary Data Objects

- `Segment`
- `SegmentImpact`
- `MarketEvent`
- `EquityImpactAssessment`
- `PortfolioExposureSnapshot`
- `RiskRegimeUpdate`
- `EvidenceClaim`

### Sections

- Segment topology: model progress, hyperscaler capex, accelerators, HBM/memory, foundry/CoWoS/semicap, networking, datacenters, power/grid, cooling/electrical, sovereign/export controls, and software monetization.
- Segment state panel: accelerating, constrained, stable, deteriorating, policy-risk, or unknown.
- First/second-order ticker map.
- Bottleneck tracker.
- Portfolio exposure overlay.
- Evidence and contradiction panel.

### Card/Table Fields

- Segment
- State
- Latest catalyst
- Event count
- First-order tickers
- Second-order tickers
- Portfolio exposure
- Watchlist exposure
- Risk flags
- Evidence ids
- Contradiction count
- Last update

### LLM-Generated Elements

- Segment movement explanation.
- First/second-order impact narrative.
- Bottleneck summary.
- Contradiction summary.
- Ticker research prompts.

### Deterministic Elements

- Segment taxonomy.
- Segment state from persisted impact records.
- Exposure totals.
- Evidence freshness.
- Missing mapping flags.
- Portfolio overlap.

### Empty/Loading/Error State

- Empty: render canonical segment skeleton and mark all states unknown.
- Loading: show latest segment-map run stages.
- Error: distinguish missing segment mappings, stale evidence, and failed exposure load.

### Acceptance Criteria

- Segment changes cite one or more evidence-backed `MarketEvent`s.
- First-order and second-order ticker impacts are visually distinct.
- Exposure is read from portfolio data, not calculated in UI.
- Segment map does not offer trade execution.

### Out Of Scope

- Arbitrary graph editing.
- Manual segment scoring in UI.
- Generic sector/ETF browsing.
- Execution or order workflows.

## 4. Ticker Analyst Workbench

### User Question

What is the current evidence-backed thesis for this ticker, what changed, what invalidates it, and what should I review before making a manual decision?

### Primary Decision Supported

Decide whether to maintain, revise, pause, invalidate, or escalate a ticker thesis and related trade plan.

### Primary Data Objects

- `EquityImpactAssessment`
- `MarketEvent`
- `EvidenceItem`
- `EvidenceClaim`
- `SignalBundle`
- `ValuationContext`
- `TradePlan`
- `RiskRegimeUpdate`
- `RecommendationArtifact`
- `ModelRun`

### Sections

- Ticker header: company, segment exposures, advisory label, data freshness.
- Thesis stack: bull case, bear case, base case, invalidation, and open questions.
- Catalyst history.
- Evidence claims and source spans.
- Signal summary: strategic thesis, technical context, forward indicators, risk.
- Valuation context link.
- Trade plan link.
- Contradictions and stale thesis warnings.

### Card/Table Fields

- Ticker
- Company
- Segment exposure
- Advisory label
- Thesis confidence
- Bull case
- Bear case
- Invalidation condition
- Latest catalysts
- Evidence ids
- Claim ids
- Signal bundle id
- Valuation scenario ids
- Trade plan id
- Model run ids
- Review status

### LLM-Generated Elements

- Thesis summary.
- Catalyst implications.
- Bull/bear case wording.
- Contradiction explanation.
- Analyst questions.
- Journal-ready note draft.

### Deterministic Elements

- Signal scores.
- Risk flags.
- Staleness checks.
- Evidence linkage validation.
- Advisory suppression.
- Portfolio exposure references.
- Price/volume facts supplied by snapshots.

### Empty/Loading/Error State

- Empty: ticker is not in universe or lacks validated evidence.
- Loading: show evidence, signal, valuation, and trade-plan load stages.
- Error: show missing evidence, stale signal bundle, or failed ticker repository read.

### Acceptance Criteria

- Every thesis claim cites evidence.
- LLM text is separated from deterministic scores.
- Invalidation conditions are visible.
- No ticker screen contains order buttons, live trading controls, or broker links.

### Out Of Scope

- Broker position sync.
- Live order entry.
- UI-generated scores.
- Uncited thesis recommendations.

## 5. Valuation & Price Target Workbench

### User Question

What valuation scenarios are reasonable for this ticker, what assumptions drive them, and how do they compare with current price and thesis risk?

### Primary Decision Supported

Decide whether valuation supports watch, hold, accumulate, trim, avoid, or thesis review as advisory labels.

### Primary Data Objects

- `ValuationContext`
- `PriceTargetScenario`
- `FinancialSnapshot`
- `MarketSnapshot`
- `EquityImpactAssessment`
- `EvidenceClaim`
- `RiskRegimeUpdate`

### Sections

- Scenario header: ticker, as_of, current price, advisory-only label.
- Scenario table: bear, base, bull, stress, and upside/downside cases.
- Assumption panel: growth, margins, capex, multiple, discount, terminal, and segment drivers.
- Evidence support: source claims and financial snapshots behind assumptions.
- Sensitivity grid.
- Risk and invalidation panel.
- Comparison to trade plan guidance.

### Card/Table Fields

- Scenario id
- Scenario label
- Time horizon
- Assumption set
- Implied price target
- Upside/downside
- Probability/weight if provided
- Evidence ids
- Financial snapshot id
- Risk flags
- Invalidation condition
- Last updated

### LLM-Generated Elements

- Assumption narrative.
- Scenario explanation.
- Risk commentary.
- Comparison with thesis.
- Questions for analyst review.

### Deterministic Elements

- Scenario math.
- Upside/downside calculation.
- Financial ratios.
- Sensitivity outputs.
- Current price comparison.
- Staleness/data-quality checks.

### Empty/Loading/Error State

- Empty: no valuation context; show required inputs and evidence gaps.
- Loading: show financial snapshot, assumptions, and scenario calculation stages.
- Error: show invalid assumptions, stale market price, or missing financial snapshot.

### Acceptance Criteria

- Price targets are labeled scenarios.
- Assumptions and evidence ids are visible.
- LLM commentary cannot overwrite scenario math.
- No target is presented as a guaranteed outcome or executable instruction.

### Out Of Scope

- Automated order sizing.
- Broker target orders.
- UI-side valuation calculation.
- Uncited price targets.

## 6. Trade Plan Workbench

### User Question

What is the advisory trade plan for this ticker, what conditions must be true, and what would invalidate or pause the plan?

### Primary Decision Supported

Decide whether a manual trade plan is ready, blocked, stale, invalidated, or journal-ready.

### Primary Data Objects

- `TradePlan`
- `EntryExitLevelSet`
- `RecommendationArtifact`
- `SignalBundle`
- `ValuationContext`
- `RiskRegimeUpdate`
- `EvidenceItem`
- `ManualTradeJournalEntry`

### Sections

- Plan header: ticker, advisory action, horizon, status, and local-only labels.
- Setup conditions: catalyst, valuation, technical, risk, liquidity, and portfolio conditions.
- Entry guidance: scenario-based entry zones.
- Exit/trim guidance: scenario-based exit and trim zones.
- Manual decision checklist: evidence, scenario, risk, exposure, and journal prerequisites.
- Invalidation panel.
- Blocking checks.
- Journal readiness panel.
- Evidence and audit links.

### Card/Table Fields

- Trade plan id
- Ticker
- Advisory action
- Horizon
- Status
- Entry guidance
- Exit guidance
- Trim guidance
- Invalidation
- Required evidence ids
- Signal bundle id
- Target weights id if relevant
- Risk checks
- Journal status
- Last reviewed

### LLM-Generated Elements

- Setup explanation.
- Risk narrative.
- Plan contradiction critique.
- Analyst checklist.
- Draft local journal note.

### Deterministic Elements

- Entry/exit levels supplied by persisted objects.
- Constraint checks.
- Risk flags.
- Target weight references.
- Staleness and missing-evidence gates.
- Publication/suppression checks.

### Empty/Loading/Error State

- Empty: no trade plan; show eligible source objects needed to create one in a future workflow.
- Loading: show plan, evidence, signals, valuation, and risk checks.
- Error: show missing evidence, invalid target weights, stale valuation, or active risk freeze.

### Acceptance Criteria

- Entry/exit levels are labeled trade-planning guidance only.
- The screen cannot submit, route, place, or execute a trade.
- Blocked plans fail closed.
- Ready status means ready for human review and possible external manual action, not ready for system execution.
- Journal capture is local-only and separate from plan readiness.

### Out Of Scope

- Order tickets.
- Routing choices.
- Execution algos.
- Broker sync.
- Automated trade loops.

## 7. Portfolio Exposure Balancer

### User Question

How does the current portfolio exposure line up with AI infrastructure segments, risk regimes, and advisory trade plans?

### Primary Decision Supported

Decide whether exposure requires review, diversification, concentration reduction, cash preservation, or plan suppression.

### Primary Data Objects

- `PortfolioExposureSnapshot`
- `Position`
- `TargetWeights`
- `RiskRegimeUpdate`
- `SegmentImpact`
- `TradePlan`
- `RecommendationAudit`

### Sections

- Portfolio summary: gross/net exposure, cash, concentration, and advisory-only label.
- Segment exposure table.
- Ticker concentration table.
- Correlation and crowding view.
- Risk regime impact.
- Target weight comparison.
- Rebalance review list.
- Manual review queue for concentration, diversification, cash, and suppression decisions.
- Suppression and constraint warnings.

### Card/Table Fields

- Ticker
- Position weight
- Target weight
- Weight difference
- Segment
- Risk contribution
- Concentration flag
- Liquidity/capacity flag
- Open trade plan id
- Advisory status
- Evidence/risk links
- Last updated

### LLM-Generated Elements

- Exposure narrative.
- Concentration critique.
- Segment crowding explanation.
- Risk regime interpretation.
- Analyst review prompts.

### Deterministic Elements

- Position weights.
- Target weights.
- Cash floor checks.
- Concentration checks.
- Theme exposure checks.
- Correlation/crowding metrics.
- Risk flags.
- Constraint validation.

### Empty/Loading/Error State

- Empty: no portfolio snapshot; show required local input/import/journal sources.
- Loading: show positions, target weights, risk, and segment exposure stages.
- Error: show stale portfolio snapshot, invalid target weights, or failed risk load.

### Acceptance Criteria

- Balancing output is advisory review only.
- Target weights are generated by deterministic portfolio code.
- No rebalance action can become an order or broker instruction.
- Rebalance review items link to trade-plan or ticker workbenches, not execution tickets.
- All warnings link to deterministic checks or evidence.

### Out Of Scope

- Automated rebalancing.
- Broker allocation.
- Order basket creation.
- UI-side target-weight generation.

## 8. Manual Trade Journal + PnL Review

### User Question

What manual trades did I record, how did they perform, and what should I learn from the decision process?

### Primary Decision Supported

Decide whether to update outcome notes, mark plan adherence, revise a thesis, or improve future trade plans.

### Primary Data Objects

- `ManualTradeJournalEntry`
- `TradePlan`
- `PnLSummary`
- `PortfolioSnapshot`
- `MarketSnapshot`
- `EvidenceItem`
- `OutcomeJournalEntry`

### Sections

- Local journal entry form: intended or completed manual trade record.
- Journal table.
- PnL summary.
- Decision replay: evidence, advisory label, valuation scenario, risk flags, and plan status at trade time.
- Plan adherence review.
- Evidence available at decision time.
- Outcome notes and lessons.
- Repeated failure/success patterns.

### Card/Table Fields

- Journal entry id
- Ticker
- Side
- Quantity
- Manual price
- Trade date
- Settlement date
- Account label
- Status
- Linked trade plan id
- Evidence available at decision time
- Realized PnL
- Unrealized PnL
- Plan adherence
- Outcome label
- Analyst note

### LLM-Generated Elements

- Outcome narrative.
- Plan adherence critique.
- Lesson summary.
- Repeated mistake/success pattern.
- Draft journal follow-up note.

### Deterministic Elements

- PnL calculations.
- Price snapshots.
- Plan adherence flags from supplied criteria.
- Journal validation.
- Evidence availability timestamps.
- Outcome metrics.

### Empty/Loading/Error State

- Empty: no local journal entries; show local journal form and remind that entries do not transmit externally.
- Loading: show journal, PnL, and linked plan load stages.
- Error: show journal persistence failure, missing market snapshot, or unavailable PnL.

### Acceptance Criteria

- Manual trade entry is local journal only.
- PnL is deterministic and never LLM-generated.
- Each completed manual trade can link to a plan or be marked unplanned.
- Journal records can describe external manual trades but cannot transmit, amend, cancel, or reconcile them with a broker.
- No broker sync, upload, transmit, order, or execution control appears.

### Out Of Scope

- Broker reconciliation.
- Tax-lot accounting.
- Live fills.
- Automated execution review.
- External trade transmission.

## 9. Advisory Update History

### User Question

How did advisory labels, thesis views, trade plans, and risk flags change over time, and what evidence caused each update?

### Primary Decision Supported

Decide whether an advisory changed for valid evidence-backed reasons and whether old assumptions need review.

### Primary Data Objects

- `RecommendationArtifact`
- `RecommendationAudit`
- `AnalystBrief`
- `TradePlan`
- `ModelRun`
- `EvidenceItem`
- `SignalBundle`
- `RunArtifact`

### Sections

- Timeline of advisory updates.
- Change diff panel.
- Evidence delta panel.
- Model run and audit links.
- Suppression and blocked-publication history.
- Ticker and segment filters.
- Exportable report view.

### Card/Table Fields

- Update id
- Ticker/portfolio scope
- Previous advisory
- New advisory
- Changed fields
- Reason summary
- Evidence ids
- Signal bundle id
- Target weights id
- Model run ids
- Audit id
- Run id
- Published at
- Suppression reason

### LLM-Generated Elements

- Change explanation.
- Evidence delta summary.
- Contradiction commentary.
- Analyst memo draft.

### Deterministic Elements

- Diff calculation.
- Audit linkage.
- Schema validation status.
- Suppression reason.
- Timestamps.
- Artifact hashes.
- Signal/target-weight ids.

### Empty/Loading/Error State

- Empty: no advisory artifacts; show required upstream chain.
- Loading: show timeline and audit fetch progress.
- Error: show missing audit, invalid artifact, or stale run references.

### Acceptance Criteria

- Every update has evidence ids or is marked suppressed/unavailable.
- Historical advisory changes are immutable read-only records.
- No update history item can trigger a trade.
- LLM-generated explanations are linked to model run ids.

### Out Of Scope

- Editing historical recommendations.
- Broker audit import.
- Compliance-grade order surveillance.
- Execution history.

## 10. Evidence Library

### User Question

What evidence supports the workstation's advisory insights, where did it come from, and is it fresh, licensed, and usable?

### Primary Decision Supported

Decide whether evidence can support a thesis, catalyst, valuation assumption, risk flag, or trade plan.

### Primary Data Objects

- `EvidenceItem`
- `EvidenceChunk`
- `EvidenceClaim`
- `SourceItem`
- `MarketEvent`
- `ModelRun`
- `DataQualityCheck`

### Sections

- Search and filters: ticker, segment, source, date, data class, license, review status.
- Evidence table.
- Claim browser.
- Source provenance drawer.
- Chunk/span viewer.
- License and data-class panel.
- Model run extraction audit.
- Evidence-to-advisory usage links.

### Card/Table Fields

- Evidence id
- Source URI
- Source type
- License label
- Data class
- Tickers/themes
- Content hash
- Ingested at
- Available at
- Claim ids
- Span refs
- Model run ids
- Review status
- Usage links

### LLM-Generated Elements

- Evidence summary.
- Claim extraction.
- Ticker/theme classification.
- Contradiction notes.
- Source quality commentary.

### Deterministic Elements

- Content hash.
- Chunk ids.
- Span refs.
- Data-class policy.
- License metadata.
- Freshness status.
- Quarantine/rejection status.
- Evidence usage links.

### Empty/Loading/Error State

- Empty: no evidence for filters; show source-monitoring and manual evidence entry paths.
- Loading: show search/index retrieval progress.
- Error: show failed query, inaccessible source, policy denial, or missing provenance.

### Acceptance Criteria

- Every evidence item displays provenance, content hash, data class, and license label.
- Private research is clearly local-only.
- Quarantined evidence cannot be used by advisory screens.
- All advisory insights can navigate back to supporting evidence.

### Out Of Scope

- Committing private reports.
- Redistributing licensed content.
- Editing source text in place.
- Broker or execution functions.
