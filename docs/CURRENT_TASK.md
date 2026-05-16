# Current Task

## Task

Finish the remaining v1.1 source-quality cleanup items from the cloud run:

1. Replace the Data Center Dynamics ticker search source that returns 403 with a crawlable configured public feed.
2. Lower GDELT crawl pressure/backoff exposure so public sentiment/news flow does not generate bursty per-ticker 429s.
3. Keep EIA/FRED/Finnhub as optional-secret sources, verify they skip cleanly when absent, and document the missing cloud secret state without storing placeholder secrets.

## Product Objective

Improve the reliability of DB-backed daily brief inputs by keeping crawler output configured, public, provenance-backed, evidence-linked, and low-pressure before downstream advisory generation.

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
- source-registry validation and seed planning under `packages/core/src/ai_infra_fund_core/equity_intelligence/` only if needed
- deterministic crawl failure/backoff handling under `services/worker/src/ai_infra_fund_worker/crawl/` only if needed
- focused worker smoke scripts under `scripts/`
- environment documentation templates
- active task and build-log docs
- focused tests under `tests/`

## Forbidden Changes

- no dependency changes
- no frontend changes
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

- Data Center Dynamics uses a configured public RSS feed instead of the blocked search page.
- GDELT uses lower-pressure configured crawling and avoids per-ticker burst fanout.
- Registry changes stay within configured public sources and do not add new source categories.
- Optional-secret sources still skip cleanly when credentials are absent and never store secret placeholders in frontier URLs.
- No broker/order/execution route or UI surface is introduced.
- No application frontend, read-only API, dependency, migration, or model-router changes are introduced.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed
python3 -m compileall packages/core/src/ai_infra_fund_core/equity_intelligence services/worker/src/ai_infra_fund_worker/crawl tests
./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_crawl_scheduler_config tests.test_crawl_advisory_materialization
git diff --check
```

Final integration may additionally run:

```bash
./.venv/bin/python -m unittest discover -s tests
```

## Definition Of Done

- Targeted verification passes.
- Full Python verification passes unless explicitly deferred with reason.
- `docs/BUILD_LOG.md` records the remaining source-quality cleanup and cloud secret status.
- Changes are committed.
