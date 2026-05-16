# Current Task

## Task

Reconcile the latest visible six-agent shared-thread guidance with the current codebase and prepare the next bounded wave.

The latest guidance says to build the product spine in this order:

1. Contract and read-model freeze.
2. Fixture-backed PostgreSQL analyst loop.
3. Read-only APIs.
4. API-backed cockpit UI.
5. Real configured public-source coverage.
6. Governed LLM analyst extraction/review.
7. Outcome journal/evaluation.
8. Cloud runtime and ops hardening.

The repository already contains implemented and tested support for waves 0-4 plus outcome-journal and cloud hardening foundations. This task prevents future agents from repeating completed Wave 1 work and makes the next implementation gate explicit.

## Product Objective

Improve analyst brief usefulness, evidence quality, catalyst detection, and advisory implementation discipline by keeping the active harness aligned with the actual repository state.

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

- `docs/CURRENT_TASK.md`
- `docs/PARALLEL_AGENT_PLAN.md`
- `docs/plans/active/current-plan.md`
- `docs/BUILD_LOG.md`

## Forbidden Changes

- no product code
- no dependency changes
- no database migrations
- no frontend changes
- no backend runtime changes
- no deployment rollout
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

- Active plan documents state that the fixture-backed DB loop, read-only APIs, API-backed cockpit, deterministic configured crawler runtime, outcome-journal foundation, and cloud runtime hardening already exist.
- Active plan documents identify remaining gaps without starting them implicitly.
- Next recommended implementation gate is bounded to governed public-source and LLM analyst extraction/review work.
- Advisory-only, no broker/order/execution, deterministic math, model routing, PostgreSQL/pgvector, and private-research guardrails remain preserved.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api
./.venv/bin/python -m unittest tests.test_research_extractor_stub tests.test_crawl_worker_loop
./.venv/bin/python -m unittest tests.test_architecture_policy
git diff --check
```

## Definition Of Done

- Current task and active plan no longer point future agents at completed Wave 1 work.
- Verification commands pass.
- `docs/BUILD_LOG.md` records the reconciliation.
- Remaining implementation gaps are documented.
