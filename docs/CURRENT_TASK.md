# Current Task

## Task

Implement LLM Intelligence v1: persist governed shadow analyst draft outputs and wire the daily AI infrastructure brief worker into the existing shadow analyst pipeline.

1. Add durable `analyst.shadow_analyst_drafts` storage and repository support.
2. Build an `AnalystContextBundle` from daily worker inputs.
3. Invoke `GovernedShadowAnalystPipeline` from the daily brief worker in shadow/stub mode.
4. Persist `review_required`, `rejected`, `fallback`, and denied audit outcomes without publishing raw LLM output.
5. Record and link a `ModelRun` for every model-mediated or attempted model-mediated path.
6. Preserve deterministic daily brief publication and fallback behavior when no model client is available.

## Product Objective

Move from deterministic-only DB-backed daily briefs toward governed, auditable LLM-mediated advisory intelligence while preserving deterministic publication gates and advisory-only boundaries.

## Governing Docs And Specs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/PARALLEL_AGENT_PLAN.md`
- `docs/plans/active/current-plan.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0012-data-architecture.md`
- `docs/ANALYST_OBJECT_MODEL.md`
- `docs/LLM_ANALYST_PROMPT_PACK.md`

Specs are canonical. If this task conflicts with a spec, the spec wins.

## Allowed Files

- shadow analyst core package under `packages/core/src/ai_infra_fund_core/shadow_analyst/` only if needed
- API migrations and repositories under `services/api/`
- daily brief worker integration under `services/worker/src/ai_infra_fund_worker/daily_ai_infra_brief_run.py`
- worker shadow-draft persistence helpers
- focused daily worker and repository tests under `tests/`
- active task and build-log docs

## Forbidden Changes

- no dependency changes
- no frontend changes
- no broker integration
- no live order placement
- no execution endpoints
- no execution-like UI controls
- no unmanaged model calls
- no real LLM SDK calls in this slice
- no raw LLM output publication
- no private_research cloud calls
- no model names hard-coded in business logic
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, scenario math, PnL, readiness checks, or publication gates
- no DuckDB/Parquet v1 dependency

## Acceptance Criteria

- Daily brief worker creates shadow draft records in stub/shadow mode.
- Invalid shadow output is persisted as rejected with validation errors.
- Fallback path is auditable and linked to a failed `ModelRun`.
- Private data denial records a denied `ModelRun` and does not call the model client.
- `ModelRun` IDs link to persisted draft rows and analyst brief payload metadata.
- Existing deterministic daily brief generation still works.
- No broker/order/execution route or UI surface is introduced.
- No application frontend, dependency, or model-router changes are introduced.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.advisory.test_shadow_analyst_pipeline tests.worker.test_shadow_analyst_draft_repository tests.test_daily_ai_infra_brief_run tests.test_advisory_workstation_read_model_migration tests.test_migration_prefix_uniqueness
./.venv/bin/python -m unittest discover -s tests
python3 -m compileall packages services tests
docker compose config
scripts/run_daily_ai_infra_brief_once.sh
git diff --check
```

## Definition Of Done

- Targeted verification passes.
- Full Python verification either passes or has unrelated pre-existing drift recorded in `docs/BUILD_LOG.md`.
- `docs/BUILD_LOG.md` records LLM Intelligence v1 implementation and verification.
- Changes are committed.
