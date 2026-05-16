# Current Task

## Task

Implement the v1.1 source-quality cleanup from the v1 completion report:

1. Improve deterministic public-source extraction so low-signal captures such as raw JSON snippets, provider messages, and generic search pages do not become misleading MarketEvent titles.
2. Tune configured public-source registry URLs that returned avoidable 403/404 responses during the bounded cloud crawler pass.
3. Persist a crawler `EvidenceItem` for successful public captures so SourceSignals and MarketEvents point at durable evidence, not only a synthetic evidence ID.

## Product Objective

Improve the usefulness of DB-backed daily brief inputs by keeping crawler output configured, public, provenance-backed, evidence-linked, and less noisy before downstream advisory generation.

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
- deterministic crawl extraction/materialization under `packages/core/src/ai_infra_fund_core/equity_intelligence/`
- crawl worker wiring under `services/worker/src/ai_infra_fund_worker/crawl/` only if needed
- focused worker smoke scripts under `scripts/`
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

- Deterministic extraction uses better public-source summaries when a captured title is generic, raw JSON-like, provider boilerplate, or search-result boilerplate.
- Crawler output remains advisory-only and evidence-linked.
- Successful public crawl captures persist an `EvidenceItem` and link legacy `EquityEvent`, `SourceSignal`, and `MarketEvent` rows to that evidence ID.
- Registry changes stay within configured public sources and do not add new source categories.
- Optional-secret sources still skip cleanly when credentials are absent and never store secret placeholders in frontier URLs.
- No broker/order/execution route or UI surface is introduced.
- No application frontend, read-only API, dependency, migration, or model-router changes are introduced.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.test_crawl_extraction tests.test_event_extractor_deterministic tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed
./.venv/bin/python -m unittest tests.worker.test_crawl_materialization_loop tests.test_crawl_worker_loop tests.test_crawl_advisory_materialization
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
- `docs/BUILD_LOG.md` records the v1.1 source-quality cleanup.
- Changes are committed.
