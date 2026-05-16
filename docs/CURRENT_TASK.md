# Current Task

## Task

Implement the next advisory-workstation phase from the shared planning thread:

1. Add a deterministic `daily_ai_infra_brief_run` worker that builds the current `AnalystBrief` and publishable `TradingAdvisory` rows from DB-backed read models.
2. Add configured public-source registry support for the crawler seed path.

## Product Objective

Move beyond fixture-only cockpit data by generating the daily brief from persisted analyst objects and by making crawler source coverage explicitly configured, public, and auditable.

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

- configured public-source registry files under `config/`
- source-registry validation and seed planning under `packages/core/src/ai_infra_fund_core/equity_intelligence/`
- crawl seed wiring under `services/worker/src/ai_infra_fund_worker/crawl/`
- daily brief worker code under `services/worker/src/ai_infra_fund_worker/`
- worker run scripts under `scripts/`
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

- `daily_ai_infra_brief_run` reads current DB-backed analyst objects and writes readiness-gated `TradingAdvisory` rows plus an `AnalystBrief`.
- The daily worker persists an `audit.run_artifacts` record and returns a stable run summary.
- The daily worker suppresses candidates with missing evidence, stale sources, disallowed data classes, unresolved contradictions, or restricted publication language.
- `config/source_registry.yaml` defines configured public sources for primary, specialist, news/API, and social-attention tiers.
- Crawl seeding can use the source registry, skips optional-secret sources when credentials are absent, and never stores secret placeholders in frontier URLs.
- No broker/order/execution route or UI surface is introduced.
- No application frontend, read-only API, dependency, or migration changes are introduced.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.test_daily_ai_infra_brief_run tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed
python3 -m compileall packages/core/src/ai_infra_fund_core/equity_intelligence services/worker/src/ai_infra_fund_worker tests
./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_crawl_scheduler_config tests.test_crawl_advisory_materialization
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
- `docs/BUILD_LOG.md` records the daily brief/source-registry pass.
- Changes are committed.
