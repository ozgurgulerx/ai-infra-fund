# Changelog

## v1.0 - Release Candidate

### Included

- Advisory-only AI Infrastructure Trading Advisory Workstation.
- Source registry driven public-source monitoring.
- Configured public-source crawler materialization into `EvidenceItem`, `SourceSignal`, and `MarketEvent` records.
- DB-backed `AnalystBrief` and `TradingAdvisory` generation.
- API-backed Daily Trading Cockpit, ticker workbench, segment map, portfolio exposure, and outcome journal endpoints.
- Governed shadow analyst pipeline with `ModelRun` audit.
- Fallback-safe model-call behavior for success, failure, timeout, denial, and fallback paths.
- Deterministic quality gate and manual review foundation.
- PostgreSQL + pgvector v1 data spine.

### Guardrails

- No broker integration.
- No live order placement.
- No order routing.
- No execution endpoint.
- No execution UI.
- No automated trading.
- No automatic LLM promotion.
- Raw LLM drafts are not published directly.
- LLM failures are fallback-safe and audited.
- Deterministic code owns scores, risk math, target weights, entry/exit levels, PnL, readiness checks, and publication/suppression gates.

### Validation Snapshot

- Python suite passed: 744 tests, 3 skipped.
- Architecture and OpenAPI sync tests passed: 44 tests.
- `compileall` passed.
- Frontend build passed.
- `npm audit --omit=dev --prefix apps/web` passed with 0 vulnerabilities.
- Docker Compose config and compose smoke passed.
- Cloud API and worker were observed `1/1` ready.
- Cloud health/readiness passed through the frontend proxy.
- Latest cloud daily brief and trading advisory endpoints returned DB-backed advisory data.

### Known v1.1 Follow-Ups

- Automatic draft promotion.
- LLM review-status UI if not already deployed.
- Quality-gate status panel if not already deployed.
- Scheduled production automation.
- External valuation-data integrations.
- Full portfolio analytics.
- External analyst consensus.
- Broader source-provider hardening.
- Making the latest real LLM call always succeed.
- Expanded source freshness monitoring and alerting.
- Deeper analyst-brief scoring calibration against outcome journal history.
