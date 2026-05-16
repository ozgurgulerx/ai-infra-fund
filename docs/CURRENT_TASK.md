# Current Task

## Task

Implement the first Wave 5 read-model enrichment slice for the AI Infrastructure Trading Advisory Workstation.

The previous reconciliation pass found that richer workstation feeds were still mostly preserved inside fixture payloads rather than first-class PostgreSQL read-model outputs. This pass promotes a bounded subset into durable read models and read-only advisory APIs.

## Product Objective

Make the Segment Map, Ticker Workbench, and Portfolio Exposure views addressable through the same advisory-only read-model spine as the Daily Trading Cockpit.

## Governing Docs And Specs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/PARALLEL_AGENT_PLAN.md`
- `docs/plans/active/current-plan.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0012-data-architecture.md`
- `docs/specs/0016-equity-intelligence-crawler.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`

Specs are canonical. If this task conflicts with a spec, the spec wins.

## Allowed Files

- additive migrations under `services/api/migrations/`
- advisory workstation repository and route code under `services/api/src/ai_infra_fund_api/`
- fixture persistence under `services/worker/src/ai_infra_fund_worker/fixture_advisory_run.py`
- OpenAPI docs under `docs/api/openapi.yaml`
- active task, plan, and build-log docs
- focused tests under `tests/`

## Forbidden Changes

- no dependency changes
- no frontend changes
- no deployment rollout unless explicitly requested after verification
- no broker integration
- no live order placement
- no execution endpoints
- no execution-like UI controls
- no arbitrary crawling
- no private-document crawling
- no paid-report scraping
- no unmanaged model calls
- no model names hard-coded in business logic
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, scenario math, PnL, readiness checks, or publication gates
- no DuckDB/Parquet v1 dependency

## Acceptance Criteria

- Additive PostgreSQL migrations define first-class read models for `RiskRegimeUpdate`, `TradePlan`, `PortfolioExposureSnapshot`, and `LLMAnalystNote`.
- Fixture advisory seeding persists those read models while preserving the existing analyst brief loop.
- Read-only API routes exist for:
  - `/internal/segment-map/latest`
  - `/internal/ticker/{ticker}/workbench`
  - `/internal/portfolio/exposure/latest`
- Routes return advisory-only envelopes and reject mutation methods.
- No broker/order/execution route or UI surface is introduced.
- OpenAPI docs are regenerated.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api
./.venv/bin/python -m unittest tests.test_openapi_export_sync tests.test_architecture_policy
python3 -m compileall services/api/src/ai_infra_fund_api services/worker/src/ai_infra_fund_worker tests
git diff --check
```

Final integration may additionally run:

```bash
./.venv/bin/python -m unittest discover -s tests
```

## Definition Of Done

- RED tests were committed before implementation.
- Targeted verification passes.
- Full Python verification passes unless explicitly deferred with reason.
- `docs/BUILD_LOG.md` records the read-model enrichment pass.
- Changes are committed and pushed.
