# Product

## Mission

Build a private, local-first, cloud-model-assisted AI Infrastructure Trading Advisory Workstation.

The product continuously monitors public macro, micro, thematic, company, financial, and sector-level information related to the AI infrastructure ecosystem. It turns that source stream into evidence-backed trading advisory, trend analysis, valuation context, risk updates, portfolio exposure awareness, and manual trade-planning support.

The product is advisory and reporting only. It helps a human analyst understand what changed, what matters, what risks moved, how current exposure is affected, and what manual journal entries or trade-plan reviews may be needed.

## Product Boundary

This is an advisory and reporting workstation, not an autonomous trading system.

Hard boundaries:

- no broker integration
- no live order placement
- no automated trading
- no execution endpoint
- no execution UI
- no broker credentials
- no order routing
- no hidden execution path
- manual trade journal only
- advisory and reporting only

Allowed outputs:

- evidence-backed trading advisory labels such as watch, accumulate, hold, trim, avoid, and exit-candidate
- daily and intraday briefs
- market, company, sector, and thematic trend analysis
- valuation context and scenario framing
- risk regime updates
- portfolio exposure awareness
- deterministic target-weight suggestions and constraint checks
- manual trade-plan support
- local journal entries for intended or completed manual trades
- outcome review, scenario replay, signal calibration, and thesis-quality evaluation

Forbidden outputs or surfaces:

- broker integration or broker credentials
- live order placement
- order routing
- execution algorithms
- automated trading
- execution endpoints
- execution-like UI controls
- broker account status or margin views
- LLM-owned final scores, constraints, target weights, execution decisions, or PnL calculations

## Primary Product Loop

```text
Source Monitoring
-> EvidenceItem
-> MarketEvent
-> SegmentImpact
-> EquityImpactAssessment
-> ValuationContext
-> RiskRegimeUpdate
-> TradingAdvisory
-> Daily/Intraday Brief
-> Manual Trade Journal
-> Outcome Review
```

The loop is designed for daily and intraday analyst work:

- monitor sources
- extract and validate evidence
- identify AI infrastructure market events
- map events to segments and tickers
- assess equity-level implications
- add valuation context
- update risk regime state
- produce advisory-only trade planning support
- brief the analyst
- record local manual trade notes
- review outcomes and improve thesis quality

## Core Monitored Domains

The workstation monitors public information across the AI infrastructure stack:

- AI model progress
- hyperscaler capex
- AI accelerators
- HBM / memory
- foundry / CoWoS / semicap
- networking / interconnect
- datacenter providers
- power / grid / nuclear / gas
- cooling / electrical infrastructure
- sovereign AI / export controls / security
- software monetization
- macro rates / liquidity / risk appetite
- company financials and valuation

## Product Shape

The product is a read-heavy analyst cockpit with local journal support:

- source monitoring and evidence provenance
- AI infrastructure catalyst detection
- segment and ticker impact mapping
- equity thesis and valuation context
- deterministic signals and portfolio exposure analysis
- advisory trade plans with local journal readiness checks
- daily and intraday analyst briefs
- trade journal and outcome review
- model-run, evidence, and recommendation audit links

The UI should feel like a focused AI infrastructure trading advisory workstation, not a generic dashboard, stock screener, marketing site, broker console, or backtesting-first quant lab.

Product and analyst-loop principles are maintained in `docs/ALPHA_ANALYST_PRINCIPLES.md`.

## Backtesting And Evaluation Role

Backtesting is not the core product experience.

Backtests, replays, and evaluation tools exist to support:

- outcome review
- scenario replay
- signal calibration
- thesis-quality evaluation
- recommendation-vs-actual comparison
- risk and bias review

They must not displace the primary daily workflow of source monitoring, evidence-backed advisory, risk review, exposure awareness, manual trade planning, and local journal review.

## Model Boundary

LLMs may classify, extract, summarize, review, critique, and explain.

Deterministic code owns:

- scores
- risk
- constraints
- target weights
- portfolio exposure calculations
- valuation scenario values when numeric
- entry/exit levels
- concentration and correlation checks
- PnL calculations
- recommendation publication checks
- recommendation suppression

All model routing must go through `config/model_profiles.yaml`. Every model call must create a `ModelRun` record. Private research is local-only by default; cloud calls must pass data-class policy.
