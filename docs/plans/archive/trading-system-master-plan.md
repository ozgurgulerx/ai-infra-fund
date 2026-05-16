# AI Infrastructure Fund Trading System Master Plan

## Summary

Build a private, local-first, advisory-only, cloud-model-assisted trading system for a personal AI infrastructure, AI ecosystem, and quantum-tech investment project. Azure AI Foundry models may assist with classification, extraction, summarization, review, and explanation. Deterministic code owns reproducible scoring, risk, backtests, constraints, and target weights.

The system behaves like a research cockpit for a small hedge-fund-style strategy, but v1 is advisory-only: it produces buy, hold, accumulate, trim, watch, and exit-candidate recommendations without placing real orders. The UI may let the user manually enter buys, sells, intended trades, and completed trades as a local trade journal, but it must not transmit orders to a broker or venue.

The institutional-quality target is process quality, not institutional headcount or spending. The system should enforce legally usable data, point-in-time correctness, explicit leakage controls, reproducible research artifacts, validation records, audit trails, model inventory, monitoring, and clear ownership of every recommendation.

The portfolio starts from the current holdings shown in the brokerage screenshot:

| Ticker | Role |
|---|---|
| MSFT | AI platform, hyperscaler, cloud capex beneficiary |
| NVDA | AI accelerator leader |
| SMCI | AI server and datacenter hardware |
| ARM | CPU/IP layer for AI and edge compute |
| RXRX | AI biotech optional satellite |
| BBAI | AI/defense optional satellite |
| Cash | Dry powder and risk buffer |

The project should use `/Users/ozgurguler/Downloads/situationalawareness.pdf` as a foundational thesis source, especially for the "trillion-dollar cluster" argument: AI compute scaling, accelerator demand, datacenter buildout, power bottlenecks, networking, cooling, advanced packaging, HBM, TSMC capacity, and national-security-driven AI infrastructure.

## Trading Strategy

Use two trading horizons:

- Strategic medium/long-term trades: 3 to 24 month positions based on AI infrastructure thesis strength, company positioning, supply-chain bottlenecks, capital spending, and valuation/risk.
- Tactical short-term overlays: 1 to 8 week add, wait, trim, or risk-warning signals based on technical indicators, news catalysts, earnings, futures/proxy markets, and portfolio concentration.

Recommendation vocabulary:

- Core Buy
- Accumulate
- Hold
- Watch
- Trim
- Avoid
- Exit Candidate

Short-term overlay vocabulary:

- Good Entry
- Wait
- Overextended
- Breakdown Risk
- Rebound Candidate

Core principle:

LLMs interpret evidence and explain recommendations. Deterministic code computes signals, risk, backtests, constraints, and target weights.

Every recommendation should also include implementation-readiness context: estimated turnover, liquidity burden, spread/slippage assumptions, expected implementation shortfall, and whether the signal is suitable for immediate action, staged accumulation, or watch-only status.

## Opportunity Map

The system should maintain a thesis map from source documents, SemiAnalysis reports, filings, news, and futures data into investable opportunity buckets.

Initial buckets:

| Theme | Examples |
|---|---|
| AI accelerators and chips | NVDA, AMD, AVGO, ARM, TSM, ASML |
| HBM, memory, and advanced packaging | MU, Samsung, SK Hynix, TSM, INTC, ASML |
| Datacenter servers and components | SMCI, DELL, HPE, VRT |
| Networking and interconnect | ANET, AVGO, MRVL, NVDA |
| Power, grid, turbines, transformers | ETN, GEV, CEG, VST, NEE, SO, DUK |
| Cloud capex and AI platforms | MSFT, GOOGL, AMZN, META, ORCL |
| Custom silicon alternatives | Google TPU, AWS Trainium, Meta silicon, Microsoft Maia, tracked through public-company exposure |
| Data wall, synthetic data, RL | AI labs, data companies, tooling, model infrastructure |
| AI security and national security | defense AI, cybersecurity, secure datacenter infrastructure |
| Quantum tech | IBM, IONQ, RGTI, QBTS, QUBT, HON, quantum ETFs where appropriate |

Each ticker receives:

- Strategic Thesis Score
- Tactical Technical Score
- Forward Pressure Score
- Portfolio Risk Score
- Combined Recommendation
- Target Weight
- Evidence-linked explanation

## Futures And Forward Indicators

Futures are forward indicators only in v1, not tradable recommendations.

Track:

- Compute futures watchlist: CME/Silicon Data compute futures, once listed and liquid.
- GPU rental and forward curves: Silicon Data where legally accessible.
- Copper futures: electrical and datacenter infrastructure pressure.
- Natural gas and power futures: datacenter power cost and supply pressure.
- Nasdaq/S&P futures: risk-on/risk-off and AI beta context.
- Rates futures: duration and valuation pressure on high-growth AI names.

Forward Pressure Score inputs:

- Curve slope
- 1M, 3M, 6M, and 12M changes
- Contango/backwardation regime
- Volatility shock
- Cross-asset confirmation

Examples:

- Rising compute rental curve can support AI hardware scarcity and accelerator supplier theses.
- Rising power curve can support power/electrical infrastructure suppliers while pressuring hyperscaler margins.
- Rising copper can confirm grid/datacenter buildout demand but also signal capex inflation.
- Falling compute curve may suggest capacity normalization and thesis decay for scarcity-driven hardware trades.

## Data Sources

Default data posture: local-first. Market data, portfolio records, evidence artifacts, run ledgers, and deterministic outputs should be stored locally unless a spec explicitly allows otherwise. Cloud models may be called through Azure AI Foundry only for allowed data classes and only through the configured model router.

Initial sources:

- yfinance for equities and basic OHLCV.
- SEC/EDGAR for filings.
- CFTC COT for futures positioning and crowdedness overlays.
- FRED for macro, rates, inflation, energy, and regime features.
- RSS and news search for public news.
- Alpha Vantage if keys exist.
- Public/delayed futures or third-party futures adapters where legally available.
- Manual CSV import for portfolio positions.
- Manual trade-entry form for buys, sells, deposits, withdrawals, fees, and notes.
- Manual trade journal import/export through CSV.
- Manually supplied private reports in ignored local folders.

Optional paid or self-serve sources to evaluate later:

- Databento or dxFeed for event-level equities, futures, and FX research.
- CME DataMine or direct CME market-data products for venue-true futures data.
- Polygon/Massive-style APIs for developer-friendly US equity dashboards.
- RavenPack-style news analytics for systematic text features.
- Similarweb, Thinknum, YipitData, or other alternative data only after provenance, license, and MNPI review.

Data estate rules:

- Store raw data in an immutable landing area before cleaning.
- Maintain canonical tables for symbols, venues, timestamps, corporate actions, currencies, calendars, and sessions.
- Build point-in-time feature tables that answer: what did we know, when did we know it, and under what license could we use it?
- Separate slow-moving fundamentals, filings, and text evidence from fast market data and microstructure data.
- Track source URI, vendor, license label, content hash, retrieval time, effective time, and availability time.
- Treat market-data license and non-display use constraints as first-class metadata.
- Reject or quarantine data with unclear provenance, paid-content leakage risk, or possible MNPI contamination.
- Enforce clock/timestamp governance for backtests, event studies, and implementation-cost analysis.

SemiAnalysis policy:

- Use SemiAnalysis as a first-class AI hardware source.
- Ingest public articles and user-provided paid reports only if the user manually saves them locally.
- Do not bypass paywalls, scrape credentials, or commit paid content.
- Extract structured claims around AI accelerators, CoWoS, HBM, networking, cloud capex, datacenter economics, and power bottlenecks.

## Architecture

Use a layered architecture.

Operating planes:

- Data Plane: raw landing, canonical tables, point-in-time feature store, research warehouse, data quality checks, provenance, and license metadata.
- Research/ML Plane: research briefs, feature engineering, factor lab, experiments, backtests, model registry, validation packs, and challenger models.
- Governance Plane: model inventory, approvals, audit logs, data entitlement records, incident workflow, monitoring, and compliance evidence.
- Analyst UI Plane: read-only dashboard for portfolio analysis, signal integrity, implementation readiness, and recommendation review.

Implementation domains:

Evidence Plane:

- PDF ingestion
- SemiAnalysis/manual report ingestion
- News and filings ingestion
- Futures/proxy ingestion
- Evidence normalization
- Local evidence retrieval

Signal Plane:

- Strategic thesis scoring
- Tactical technical scoring
- Forward indicator scoring
- Portfolio risk scoring
- Target-weight generation
- Deterministic constraints

Evaluation Plane:

- Backtests
- Walk-forward tests
- Purged cross-validation and embargo windows where labels overlap
- Lookahead-bias checks
- Recursive indicator checks
- Monte Carlo stress tests
- Deflated Sharpe, Probabilistic Sharpe, and probability-of-backtest-overfitting checks
- Benchmark comparison
- Cost, slippage, liquidity, and capacity analysis
- Immutable run/audit logs

Recommended stack:

- `apps/web`: Next.js, TypeScript, Tailwind/shadcn, ECharts, TanStack Query/Table.
- `services/api`: FastAPI, typed REST endpoints, SSE run-status stream, bound to `127.0.0.1`.
- `services/worker`: Python workers for ingest, signals, scoring, model routing, and scheduled runs.
- Runtime:
  - Docker Compose for v1 local portability.
  - Separate `web`, `api`, `worker`, `postgres`, and `migrate` services.
  - Kubernetes or hosted orchestrators only after the Compose service boundary proves insufficient.
- Storage:
  - PostgreSQL + pgvector for canonical facts, portfolio records, trade journal, evidence metadata, evidence claims, embeddings, run ledger, model runs, market snapshots, factor rows, signal bundles, target weights, recommendation artifacts, audits, backtest summaries, evaluation results, and local semantic retrieval.
  - Ignored local filesystem for raw PDFs, CSVs, downloaded reports, and exports, with metadata and hashes in PostgreSQL.
  - DuckDB + Parquet only as a future analytical scale-out option if large local analytics outgrow PostgreSQL.
  - Optional Delta Lake layout later if local files move to object storage or multi-writer workflows.
  - Azure Search remains optional and is not required for v1.
- Orchestration:
  - Start with simple scheduled worker jobs.
  - Evaluate Dagster later if asset lineage, backfills, and data-quality checks become complex.
- Experiment tracking:
  - Add MLflow once there are trained models or many factor experiments.
  - Keep model inventory and validation metadata even before MLflow exists.
- Time-series serving:
  - PostgreSQL remains the v1 research and application workhorse.
  - Evaluate DuckDB/Parquet, ClickHouse, QuestDB, or TimescaleDB only if intraday/event-level queries or large backtest matrices outgrow PostgreSQL.

## Agent Roles

Agents should output structured artifacts with evidence IDs. They should not own final numeric scores or target weights.

Initial agents:

- Thesis Agent: extracts thesis themes from Situational Awareness, SemiAnalysis, filings, and research reports.
- Market Data Agent: fetches and caches OHLCV, prices, volume, splits, and dividends.
- Technical Agent: computes RSI, MACD, moving averages, Bollinger bands, ATR, trend, momentum, and volume indicators.
- Forward Indicators Agent: computes futures/proxy pressure signals.
- News Agent: ingests headlines, filings, RSS, and public web evidence.
- Portfolio Risk Agent: computes concentration, cash drag, theme exposure, volatility, drawdown, and liquidity risk.
- Decision Explainer Agent: explains deterministic scores and target weights using cited evidence.
- Adversarial Reviewer Agent: identifies contradiction, missing evidence, stale thesis, and overconfidence.
- Validation Agent: checks whether a strategy or model has required research brief, dataset snapshot, validation protocol, cost model, and approval metadata.
- Data Quality Agent: reports missing records, stale features, schema changes, timestamp drift, and entitlement exceptions.

## Research Workflow And SOPs

Every strategy or factor starts with a research brief:

- thesis and market intuition
- expected edge horizon
- asset universe
- required data
- label definition
- expected implementation path
- likely failure modes
- capacity and liquidity assumptions

Research-to-production gate:

- written research brief
- point-in-time data evidence
- leakage-aware validation method
- walk-forward backtest with fees, slippage, liquidity filters, and turnover
- benchmark comparison versus simple baselines
- model card or strategy card
- explicit failure modes
- adversarial review or self-challenge memo
- registry entry with versioned artifacts

Data-change SOP:

- upstream schema, vendor, license, or calendar changes trigger impact analysis
- rerun canonical-table regression tests
- refresh data-quality dashboard
- rerun benchmark backtests where affected
- promote only after the model owner signs off

Incident SOP:

- freeze affected recommendation publication on data outage, timestamp drift, large residual, signal anomaly, or LLM validation failure
- snapshot evidence and run artifacts
- compare current output with prior version and fallback path
- document root cause and remediation
- re-enable only after post-mortem and validation checks pass

## Model Routing

Use a configurable model router. Do not hard-code model names in business logic.

Cloud model context:

- Provider: Azure AI Foundry
- Project: `ozgurguler-7212`
- Region: `northcentralus`
- Endpoint: `https://ozgurguler-7212-resource.services.ai.azure.com/api/projects/ozgurguler-7212`

Initial routing defaults:

| Role | Default |
|---|---|
| Source classification, dedupe, light metadata | gpt-5-nano |
| Evidence summaries and draft recommendation narratives | DeepSeek-V4-Flash |
| Structured orchestration, schema repair, validation retries | gpt-5-mini |
| Adversarial thesis review and contradiction checks | Kimi-K2.6 |
| Local fallback | qwen3:30b, deepseek-r1:32b |
| Embeddings | local bge-m3 first |

Model routing details live in the separate plan:

- `docs/plans/model-routing-and-audit-plan.md`

Related planning files:

- `docs/plans/data_plan.md`
- `docs/plans/llm_plan.md`
- `docs/plans/deployment_harness.md`
- `docs/plans/goal_plan.md`

## Contracts

Core contracts:

- `Position`: ticker, quantity, cost basis, account, asset type, notes.
- `TradeEntry`: trade ID, ticker, side, quantity, price, fees, trade date, settlement date, account, status, source, notes.
- `TradeJournal`: append-only list of manual, imported, intended, paper, and completed trades.
- `UniverseMember`: ticker, theme, role, max weight, watchlist status, thesis source.
- `DatasetSnapshot`: dataset ID, source, license label, retrieval time, effective time, availability time, content hash, schema version.
- `EvidenceItem`: evidence ID, source URI, content hash, timestamp, license label, tickers, themes, summary.
- `EvidenceClaim`: claim ID, evidence ID, ticker/theme, claim type, direction, magnitude, time horizon, confidence, span reference.
- `FeatureSet`: feature set ID, dataset snapshot IDs, formula version, point-in-time availability rule, owner.
- `SignalBundle`: strategic thesis score, tactical technical score, forward pressure score, portfolio risk score, formula versions.
- `TargetWeights`: ticker weights, cash weight, constraints, source signal IDs.
- `ImplementationEstimate`: expected turnover, spread cost, slippage, participation, liquidity limit, implementation shortfall.
- `BacktestRun`: strategy ID, dataset snapshot IDs, validation protocol, cost assumptions, metrics, artifact hash.
- `ModelInventoryEntry`: model or strategy ID, owner, purpose, inputs, approval status, validation date, retraining trigger, retirement criteria.
- `RecommendationAudit`: recommendation ID, target weights ID, evidence IDs, signal bundle ID, model runs, deterministic checks, reviewer findings.
- `IncidentRecord`: incident ID, severity, affected artifacts, freeze status, root cause, remediation, reopen criteria.
- `DataQualityCheck`: dataset ID, check name, status, severity, observed value, threshold, timestamp.
- `RunArtifact`: immutable output from a daily or on-demand run.

## UI

The first screen should be the working dashboard, not a landing page.

Frontend implementation should use `everything-claude-code:frontend-patterns` for React/Next.js patterns and `everything-claude-code:e2e-testing` for critical UI flows. A dedicated project-local frontend implementation skill may be added later at `.agents/skills/fund-frontend-implementation/SKILL.md`.

The visual bar is modern and polished: a serious trading control room with dense but readable information, crisp typography, responsive layouts, restrained color, clear status/risk indicators, and accessible controls. Avoid marketing-page composition, decorative hero sections, and toy dashboard styling.

Views:

- Portfolio
- Trade Entry
- Trade Journal
- Watchlist
- Ticker Detail
- Suggestions
- Technical Signals
- Forward Tape
- Thesis Map
- Evidence Library
- Agent Runs
- System Architecture / Ops Room
- Backtest/Evaluation
- Data Quality
- Model Registry
- Incidents
- Implementation Cost

Every suggestion must include:

- Action
- Horizon
- Target weight
- Current weight
- Score breakdown
- Evidence links
- Risks and contradicting evidence
- Data freshness and model approval status
- Estimated implementation cost
- Advisory-only label

System Architecture / Ops Room rules:

- The UI should include a system architecture map that behaves like a trading system ops room.
- Modules should include data plane, evidence plane, signal plane, portfolio engine, model router, evaluation harness, recommendation artifacts, API, worker, storage, and UI.
- Green means working and tested: required tests pass, latest health check is good, and required artifacts exist.
- Yellow means degraded, stale, partial, or untested.
- Red means failing tests, blocked health checks, incident freeze, stale critical data, or missing required artifacts.
- Gray means planned but not implemented.
- Module state must come from real test results, architecture policy checks, run artifacts, health checks, data freshness checks, or incident records. Do not fake status color in the frontend.
- Clicking a module should show latest status, spec clauses, dependency chain, artifacts, failures, and next required work.

Trade Entry rules:

- The trade-entry UI records user-entered buy/sell activity only.
- It supports statuses such as `intended`, `paper`, `completed`, `cancelled`, and `ignored`.
- It can update local positions and realized/unrealized PnL after user confirmation.
- It can compare a user-entered trade against the current recommendation and risk constraints.
- It must show advisory-only and local-journal labeling.
- It must not connect to broker APIs, place orders, route orders, or expose an execution endpoint.

## Spec-Driven Programming

Create specs before implementation:

- `docs/specs/0001-product-vision.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0004-agent-contracts.md`
- `docs/specs/0005-ui-acceptance.md`
- `docs/specs/0006-forward-indicators.md`
- `docs/specs/0007-situational-awareness-thesis-map.md`
- `docs/specs/0008-model-routing-and-audit.md`
- `docs/specs/0009-evaluation-harness.md`
- `docs/specs/0010-repo-patterns-architecture.md`
- `docs/specs/0011-implementation-roadmap.md`
- `docs/specs/0012-data-architecture.md`
- `docs/specs/0013-llm-routing-and-governance.md`
- `docs/specs/0014-risk-monitoring-and-incidents.md`

Maintain root `AGENTS.md` as the project operating manual:

- Advisory-only rule.
- Data-source and paid-report policy.
- Secret handling.
- Agent responsibilities.
- Scoring vocabulary.
- Testing gates.
- License policy.
- Rule that deterministic modules own scores, risk, backtests, and target weights.

## Implementation Operating Model

Use a layered control system:

1. `AGENTS.md` for hard rules.
2. Repo-local skills for repeatable workflows once implementation patterns stabilize.
3. Explicit subagents for parallel review and verification.
4. Tests and policy checks as the real enforcement layer.
5. CI and non-interactive Codex runs later for repeatable review.

Do not rely on Gmail or Calendar plugins for this repo. They are installed in the broader environment but are irrelevant to the trading-system implementation, except for scheduling or planning outside the codebase.

During implementation, use existing workflow skills where relevant:

- `everything-claude-code:tdd-workflow`
- `everything-claude-code:verification-loop`
- `everything-claude-code:security-review`
- `everything-claude-code:backend-patterns`
- `everything-claude-code:api-design`
- `everything-claude-code:frontend-patterns`
- `everything-claude-code:e2e-testing`
- `everything-claude-code:eval-harness`
- `everything-claude-code:documentation-lookup`
- `everything-claude-code:coding-standards`

Create project-local skills later under `.agents/skills/`:

- `fund-phase-implementation`
- `fund-architecture-review`
- `fund-financial-safety-review`
- `fund-evaluation-review`
- `fund-model-routing-review`
- `fund-frontend-review`

Use `skill-creator` for these skills. Use `plugin-creator` later only if the workflows should be packaged as a project-local plugin.

For every implementation phase, run the phase build loop:

1. Read `AGENTS.md` and relevant specs.
2. Implement only the current phase.
3. Start with failing tests.
4. Make the implementation pass.
5. Run unit, policy, and relevant integration/evaluation checks.
6. Use parallel review subagents.
7. Fix HIGH/CRITICAL findings.
8. Report spec clauses satisfied, files changed, tests run, and remaining gaps.

## Repo Patterns To Adopt

- FinRL-X: weight-centric contract. Strategy outputs target weights, not orders.
- Qlib: research workflow with data, model/scoring, backtest, risk, portfolio optimization, and reporting.
- LEAN/Nautilus: deterministic event objects and shared semantics between daily runs and backtests.
- OpenBB: analyst-facing data integration patterns and local research surface.
- MlFinLab: finance-specific validation ideas, including leakage-aware validation, deflated Sharpe, and backtest-overfitting controls. Treat licensing and package terms carefully before direct dependency use.
- Freqtrade: dry-run discipline, config clarity, backtesting analysis, lookahead-bias checks, recursive indicator checks. Treat GPL code as reference only.
- Jesse: benchmark mode, Monte Carlo robustness, feature/label capture, and rich performance charts.
- TensorTrade/FinRL-Meta: action/reward/environment abstractions for later experiments, not production v1.
- hftbacktest: execution realism for future short-term/paper trading, not needed for v1 daily/weekly advisory signals.
- Hummingbot: connector pattern with health, auth, rate-limit, freshness, and fallback metadata.
- vn.py alpha: multi-factor templates and LightGBM/Lasso/MLP compatibility later.
- RD-Agent/Qlib factor mining: bounded Hypothesis Lab later for report-driven factor ideas, without arbitrary code execution.

## Testing And Evaluation

Unit tests:

- Indicator math.
- Curve scoring.
- Thesis scoring.
- Portfolio constraints.
- Target-weight generation.
- Trade-entry validation and position roll-forward.
- CSV validation.
- Evidence parsing.

Integration tests:

- Portfolio import.
- Manual trade entry.
- Trade journal import/export.
- Position reconstruction from trade journal.
- Ticker analysis.
- SemiAnalysis/manual-report ingestion.
- Futures/proxy fallback.
- Daily run artifact generation.
- Recommendation generation.

Evaluation tests:

- Walk-forward split enforcement.
- Purged cross-validation and embargo enforcement.
- Lookahead-bias checks.
- Recursive indicator checks.
- Monte Carlo stress on recommendation history.
- Deflated Sharpe and probability-of-backtest-overfitting reporting.
- Transaction cost, spread, slippage, liquidity, and capacity assumptions.
- Benchmark comparison versus buy-and-hold and equal-weight baskets.
- Point-in-time feature availability checks.

Safety tests:

- No order-placement endpoint exists.
- Trade-entry endpoints are journal-only and cannot call broker, route, execute, or submit modules.
- Private reports, cache, artifacts, and secrets are ignored.
- Every suggestion includes evidence IDs and advisory labeling.
- LLM failure falls back to deterministic scoring.
- No model can emit final numeric scores or target weights directly.
- Recommendations are suppressed when required data is stale, unlicensed, quarantined, or model approval is expired.
- Incident freeze status blocks publication of affected recommendation artifacts.

## Initial Build Phases

Phase 0: Governance Scaffold

- `AGENTS.md`
- `docs/specs/0001-product-vision.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0004-agent-contracts.md`
- `docs/specs/0005-ui-acceptance.md`
- `docs/specs/0006-forward-indicators.md`
- `docs/specs/0007-situational-awareness-thesis-map.md`
- `docs/specs/0008-model-routing-and-audit.md`
- `docs/specs/0009-evaluation-harness.md`
- `docs/specs/0010-repo-patterns-architecture.md`
- `docs/specs/0011-implementation-roadmap.md`
- `docs/specs/0012-data-architecture.md`
- `docs/specs/0013-llm-routing-and-governance.md`
- `docs/specs/0014-risk-monitoring-and-incidents.md`
- `docs/specs/0015-containerized-deployment.md`
- `config/model_profiles.yaml`
- `tests/test_architecture_policy.py`
- `docker-compose.yml`
- `.env.example`
- `.dockerignore`
- container Dockerfiles for `web`, `api`, and `worker`

Phase 1: Contracts And Schemas

- `Position`
- `TradeEntry`
- `TradeJournal`
- `UniverseMember`
- `DatasetSnapshot`
- `EvidenceItem`
- `EvidenceClaim`
- `FeatureSet`
- `ModelRun`
- `SignalBundle`
- `TargetWeights`
- `ImplementationEstimate`
- `BacktestRun`
- `ModelInventoryEntry`
- `RecommendationArtifact`
- `RecommendationAudit`
- `IncidentRecord`
- `DataQualityCheck`
- `RunArtifact`

Phase 2: Data Spine

- PostgreSQL + pgvector migrations.
- Local environment example.
- Data-class enum.
- Evidence chunk embedding table.
- Portfolio snapshot tables.
- Trade journal persistence.
- Position reconstruction persistence.
- Market snapshot, backtest summary, and evaluation summary persistence in PostgreSQL.

Phase 3: Model Router And ModelRun Ledger

- Model profile loader.
- Task-role model resolution.
- Fallback chains.
- Data-class policy checks.
- Prompt version registry.
- Schema validation and retry policy.
- ModelRun persistence.

Phase 4: Deterministic Signals And Portfolio

- Strategic thesis score.
- Tactical technical score.
- Forward indicator score.
- Portfolio risk score.
- Constraint validation.
- Target-weight generation.
- Recommendation-versus-trade comparison.

Phase 5: Evidence Ingestion And Provenance

- Source adapters.
- Deterministic parsing.
- Content hashing.
- Chunking.
- Local embedding generation.
- Evidence claim extraction route.
- Provenance and license handling.
- Private report local-only defaults.

Phase 6: Recommendation Artifacts And Audit

- Recommendation builder.
- Deterministic score loading.
- Deterministic target weights.
- Explanation generation.
- Adversarial review.
- Final schema validation.
- Audit persistence.

Phase 7: Evaluation Harness

- Model benchmark cases.
- Strategy benchmark cases.
- Walk-forward split checks.
- Lookahead-bias checks.
- Recursive indicator checks.
- Purged CV and embargo checks.
- Monte Carlo stress.
- Transaction cost / liquidity / slippage / capacity checks.
- Benchmark comparison.
- Shadow-mode model evaluation.

Phase 8: Local Read-Only UI

- Portfolio view.
- Trade-entry and trade-journal views.
- Evidence library.
- Recommendation audit view.
- System architecture / ops room.
- Backtest/evaluation view.
- Model run status view.
- Incident/data-quality views.
- No order placement or broker execution UI.

## Assumptions

- V1 is local-first, advisory-only, and cloud-model-assisted via Azure AI Foundry.
- Strategic medium/long-term trades are primary.
- Tactical signals are timing overlays.
- Futures are forward indicators only.
- SemiAnalysis paid content is manually supplied by the user and never scraped or committed.
- Local model fallback is useful, but deterministic scoring must work without cloud or local LLM availability.
- No brokerage integration or live order execution exists in v1.
- Market-data licensing, non-display use, and MNPI concerns are treated as design constraints even for read-only research.
- Point-in-time correctness is required before any backtest result is considered credible.
