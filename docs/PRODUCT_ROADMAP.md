# Product Roadmap

## Purpose

This roadmap turns the competitor/product scan into capability tracks for the AI Infrastructure Trading Advisory Workstation.

The direction is:

```text
AlphaSense-style evidence intelligence
+ Koyfin/YCharts-style equity and portfolio analysis
+ TradingView-style visual context
+ Glassnode/Kaiko-style forward risk indicators
specialized for the AI infrastructure equity stack
```

The product remains advisory and reporting-only. It must never automate trading, connect to brokers, route orders, expose execution controls, or store broker credentials.

## Competitive Reference Patterns

| Pattern | Reference Products | Useful Capabilities To Borrow | Boundary |
| --- | --- | --- | --- |
| Institutional terminal | Bloomberg Terminal, FactSet | Multi-source market data, news, portfolio analytics, company research, workflow depth | Do not copy execution, OMS, broker, or live trading surfaces |
| Market intelligence search | AlphaSense, Tegus, Quartr | Search across filings, transcripts, expert calls, broker research, IR docs, internal notes, cited summaries | Respect licensing, data-class routing, and private-research local-only rules |
| Equity research workbench | Koyfin, Stock Rover, Seeking Alpha, YCharts | Fundamentals, screeners, ratings, estimate revisions, dashboards, reports, portfolio comparison | Numeric scores, valuation scenarios, and PnL remain deterministic |
| Charting and technical workflow | TradingView | Fast charts, overlays, alerts, screeners, technical studies, watchlists | No broker connection, order ticket, execution, or automated trading loop |
| Portfolio analytics and loss review | YCharts, FactSet, Portfolio Visualizer-style tools | Attribution, drawdown, benchmark comparison, exposure, factor/risk decomposition | Local journal and outcome review only |
| Crypto and macro forward indicators | Glassnode, Kaiko, CME market data | BTC risk appetite, futures, open interest, funding, ETF flows, options skew, liquidity indicators | Forward indicators only, not crypto trading or broker execution |

## Capability Tracks

### 1. IR, Transcript, And Company Event Layer

Decision supported: know which company events and management commentary changed the thesis.

Primary sources:

- SEC filings and company IR pages.
- Earnings call transcripts.
- Investor presentations and capital markets day slides.
- Conference appearances.
- Press releases and product launch pages.

Core objects:

- `SourceSignal`
- `EvidenceItem`
- `EvidenceClaim`
- `MarketEvent`
- `EquityImpactAssessment`
- `ModelRun`

LLM-owned elements:

- classify source type
- extract cited claims
- summarize management commentary
- identify contradictions and open questions

Deterministic elements:

- source hashing
- duplicate detection
- timestamp/freshness checks
- data-class policy
- citation/evidence linkage validation

Acceptance criteria:

- every transcript or IR-derived insight links to an `EvidenceItem`
- private or paid research remains local-only unless explicitly routed and audited
- company events become advisory context, not trade instructions

### 2. Consensus Estimates, Revisions, And KPI Layer

Decision supported: determine whether expectations, guidance, or valuation context changed.

Primary sources:

- public company financial statements
- available consensus/estimate feeds when licensed
- earnings surprise and guidance data
- analyst target/revision data when licensed
- company KPIs such as data center revenue, backlog, gross margin, capex, HBM supply, CoWoS capacity, power availability, and AI server demand

Core objects:

- `FinancialSnapshot`
- `ValuationContext`
- `FeatureSet`
- `SignalBundle`
- `DataQualityCheck`

LLM-owned elements:

- explain what changed in plain English
- summarize guidance deltas
- draft analyst questions

Deterministic elements:

- revision calculations
- YoY/QoQ deltas
- valuation scenario math
- stale-data and missing-data gates
- formula versions

Acceptance criteria:

- estimate and valuation changes are point-in-time safe
- price targets are labeled as scenarios
- numeric valuation outputs are not created directly by an LLM

### 3. AI Infrastructure Universe Screener

Decision supported: discover which AI infrastructure names deserve review beyond the current portfolio.

Primary sources:

- configured watchlist and universe CSVs
- fundamentals and valuation data
- technical snapshots
- source-signal/catalyst counts
- segment exposure tags
- liquidity and implementation estimates

Core objects:

- `UniverseMember`
- `SegmentImpact`
- `ValuationContext`
- `SignalBundle`
- `ImplementationEstimate`
- `PortfolioExposureSnapshot`

LLM-owned elements:

- thesis summary
- segment role explanation
- risk narrative
- catalyst rationale

Deterministic elements:

- screen filters
- factor calculations
- ranking components
- liquidity checks
- exposure constraints

Acceptance criteria:

- each screened name shows why it appears
- every thesis/catalyst claim cites evidence
- screen output is advisory review priority, not an executable order list

### 4. Portfolio PnL Attribution And Loss Review

Decision supported: understand why manual trades or holdings won or lost money.

Primary sources:

- local manual trade journal
- portfolio snapshots
- market snapshots
- advisory artifacts
- market events and evidence links
- benchmark series

Core objects:

- `TradeJournal`
- `OutcomeJournalEntry`
- `PortfolioExposureSnapshot`
- `MarketEvent`
- `RecommendationArtifact`
- `BacktestRun`

LLM-owned elements:

- outcome narrative
- lesson-learned draft
- thesis-quality critique
- contradiction summary

Deterministic elements:

- realized/unrealized PnL
- benchmark-relative PnL
- drawdown
- exposure contribution
- segment attribution
- trade-plan adherence checks

Acceptance criteria:

- PnL and attribution are deterministic
- every outcome review links back to manual journal entries and advisory/evidence IDs
- losses are explained through thesis, timing, valuation, risk regime, and catalyst buckets

### 5. Event-Overlaid Charts And Technical Context

Decision supported: see price action, technical setup, and catalyst timing in one view.

Primary sources:

- market snapshot CSVs or configured market data adapters
- technical indicators
- `MarketEvent` timestamps
- advisory and journal timestamps

Core objects:

- `MarketSnapshot`
- `FeatureSet`
- `SignalBundle`
- `MarketEvent`
- `TradeJournal`

LLM-owned elements:

- chart context explanation
- contradiction notes
- analyst questions

Deterministic elements:

- technical indicators
- support/resistance scenarios
- entry/exit planning levels
- event overlay placement
- stale-data checks

Acceptance criteria:

- charts show MarketEvents, advisories, and manual journal entries as overlays
- entry/exit levels are labeled trade-planning guidance only
- no chart surface contains broker, order, route, fill, or execution controls

### 6. Internal Research Library

Decision supported: search and reuse private notes, paid reports, thesis memos, PDFs, and local research without leaking them.

Primary sources:

- local markdown notes
- local PDFs
- user thesis memos
- saved SemiAnalysis-style notes and excerpts
- manually curated source summaries

Core objects:

- `EvidenceItem`
- `EvidenceChunk`
- `EvidenceClaim`
- `DataEntitlement`
- `ModelRun`

LLM-owned elements:

- local/private summarization when routed to allowed local models
- claim extraction
- contradiction review

Deterministic elements:

- local-only policy
- content hashing
- chunking
- entitlement checks
- provenance and span refs

Acceptance criteria:

- private research is local-only by default
- cloud calls are denied unless data-class policy explicitly allows them
- evidence snippets are cited by span, not copied wholesale into unsafe outputs

### 7. Exportable Advisory Briefs

Decision supported: produce a reusable daily or intraday analyst packet.

Primary sources:

- latest analyst brief
- market events
- segment impacts
- valuation contexts
- trading advisories
- risk regime updates
- outcome journal summaries

Core objects:

- `AnalystBrief`
- `TradingAdvisory`
- `RecommendationAudit`
- `RunArtifact`
- `OutcomeJournalEntry`

LLM-owned elements:

- executive summary
- thesis deltas
- contradiction notes
- analyst questions
- journal-note draft

Deterministic elements:

- evidence/model-run completeness checks
- advisory-only labels
- suppressed-section policy
- export metadata and content hash

Acceptance criteria:

- exported reports include evidence IDs, model run IDs, run ID, and advisory-only labels
- reports can be regenerated from persisted artifacts
- no report includes execution instructions or broker/account details

### 8. Forward Indicator Expansion

Decision supported: detect risk appetite, liquidity, capacity, and macro pressure before they hit AI infrastructure equities.

Primary sources:

- CME/Nasdaq/SOX futures and open interest when available
- rates, yield curve, dollar, liquidity, VIX, MOVE, credit spreads
- BTC ETF flows, BTC CME futures/open interest, options skew, funding rates, on-chain activity where available
- power, natural gas, uranium/nuclear, datacenter power availability, and grid constraint data
- semiconductor cycle proxies such as memory pricing, HBM supply, foundry capacity, semicap orders, and export-control updates

Core objects:

- `ForwardIndicator`
- `FeatureSet`
- `RiskRegimeUpdate`
- `SignalBundle`
- `DataQualityCheck`

LLM-owned elements:

- risk regime narrative
- cross-market interpretation
- catalyst watch questions

Deterministic elements:

- indicator calculations
- thresholds
- regime classification
- stale-data checks
- formula versions

Acceptance criteria:

- forward indicators are advisory context and risk flags only
- every indicator records source, as_of, available_at, content hash, and formula version
- BTC and crypto data are used as risk-appetite context, not as trading execution features

## Priority Order

1. Finish the current product loop: crawler captures -> `SourceSignal` -> `MarketEvent` -> `AnalystBrief` -> `OutcomeJournal`.
2. Add IR/transcripts and company-event coverage.
3. Add portfolio PnL attribution and loss review.
4. Add event-overlaid charts for ticker workbench.
5. Add consensus estimates, revisions, and KPI context where data licensing allows.
6. Add AI infrastructure universe screener.
7. Add internal research library with local-only policy gates.
8. Add exportable daily/intraday advisory briefs.
9. Add BTC/CME/macro/power forward indicators.

## Product Non-Goals

- becoming a broker terminal
- live order placement
- order routing
- automated trading loops
- broker account or margin views
- unmanaged cloud-model calls
- redistributing licensed paid content
- letting LLMs own final scores, target weights, PnL, constraints, valuation math, or execution decisions

## Source References

- Bloomberg Terminal: https://www.bloomberg.com/professional/products/bloomberg-terminal/
- FactSet: https://www.factset.com/
- AlphaSense: https://www.alpha-sense.com/
- Tegus: https://tegus.com/
- Quartr: https://quartr.com/
- Koyfin: https://www.koyfin.com/
- Stock Rover: https://www.stockrover.com/
- Seeking Alpha: https://seekingalpha.com/
- YCharts: https://www.ycharts.com/
- TradingView: https://www.tradingview.com/features/
- Glassnode: https://glassnode.com/
- Kaiko: https://www.kaiko.com/
