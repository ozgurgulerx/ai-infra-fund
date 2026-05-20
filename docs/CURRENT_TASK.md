# Current Task

## Task

Repair and extend the crawl infrastructure source-registry sync so cloud crawling
matches the configured public-source list, stale disabled URLs stop leasing, and
validated easy-picking public sources are added safely.

## Product Objective

Improve source monitoring, evidence quality, catalyst detection, and advisory
brief usefulness by keeping the public crawl frontier aligned with
`config/source_registry.yaml` and avoiding hot-looping or stale crawl rows for
disabled, removed, missing-secret, or source-policy-deferred sources.

## Governing Docs And Specs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/CURRENT_TASK.md`
- `docs/specs/0016-equity-intelligence-crawler.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`
- `docs/HARNESS.md`

## Allowed Files

- `config/source_registry.yaml`
- `config/source_access_decisions.yaml`
- `docs/CURRENT_TASK.md`
- `docs/BUILD_LOG.md`
- `docs/crawl_source_validation_2026-05-18.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`
- `packages/core/src/ai_infra_fund_core/equity_intelligence/seeder.py`
- `services/api/src/ai_infra_fund_api/repositories/equity_intelligence.py`
- `services/worker/src/ai_infra_fund_worker/crawl/seed.py`
- focused crawler/source-registry tests under `tests/`
- deployment manifests/scripts required for the cloud crawl runtime rollout

## Forbidden Changes

- no broker integration
- no live order placement
- no order routing
- no execution endpoints
- no execution UI
- no automated trading loops
- no paid-report scraping, proxy bypass, stealth browser, or access-control bypass
- no activation of key-gated sources unless the configured secret exists
- no arbitrary internet discovery outside approved source-registry entries

## Acceptance Criteria

- Source registry seed plans mark skipped sources inactive when crawling is
  disabled or an optional secret is missing.
- Seeding deactivates DB source rows that are skipped, removed from the current
  registry, or no longer crawl-enabled.
- Seeding marks stale `source_registry` frontier and queue rows as `skipped`
  when their source is inactive or their URL is no longer in the current seed
  plan, while preserving historical captures and logs.
- Validated easy-picking public sources are added to `config/source_registry.yaml`
  with explicit ticker binding and public-source metadata.
- Failed or deferred easy-picking candidates are recorded in
  `config/source_access_decisions.yaml` instead of activated.
- The crawler remains HTTP-only and advisory/reporting-only.
- Cloud validation confirms the deployed crawler uses the updated source list and
  disabled/stale source rows no longer lease.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed tests.test_equity_intelligence_repository
./.venv/bin/python -m unittest tests.test_crawl_worker_loop tests.worker.test_crawl_runtime_operations tests.test_crawl_fetcher tests.test_crawl_advisory_materialization tests.worker.test_crawl_materialization_loop tests.test_crawl_scheduler_config tests.test_crawl_api_dashboard
./.venv/bin/python -m unittest tests.test_architecture_policy tests.equity_intelligence.test_restricted_inference_sources tests.equity_intelligence.test_source_access_decisions
git diff --check
```

## Definition Of Done

- RED tests are confirmed before production code changes.
- Targeted crawler/source-registry tests pass.
- Architecture policy and source-policy tests pass.
- `git diff --check` passes.
- Updated cloud deployment is validated against
  `https://ai-infra-fund-frontend.azurewebsites.net`.
- Dirty worktree state unrelated to this task is preserved and reported.
