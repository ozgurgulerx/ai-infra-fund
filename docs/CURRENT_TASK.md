# Current Task

## Task

Prepare the Agent 1-5 advisory workstation readiness wave.

This is a coordination and contract-readiness task only. It replaces the completed crawler/cloud task with a phase-scoped setup task for the next parallel workstreams:

1. Current task and repo coordination.
2. Analyst object model and contract alignment.
3. LLM analyst prompt pack.
4. Architecture policy guardrails.
5. Mock-data normalization for workstation screens.

## Product Objective

Make the AI Infrastructure Trading Advisory Workstation easier to build correctly by aligning the active task, shared object language, prompt boundaries, policy tests, and mock data before the next UI and runtime work begins.

This improves:

- evidence quality
- catalyst detection
- segment impact mapping
- equity thesis quality
- risk regime awareness
- advisory brief usefulness
- journal/outcome review quality

## Governing Docs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`
- `docs/UI_SCREEN_SPECS.md`
- `docs/SPEC_ROUTER.md`
- `docs/ANALYST_OBJECT_MODEL.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0004-agent-contracts.md`
- `docs/specs/0008-model-routing-and-audit.md`
- `docs/specs/0013-llm-routing-and-governance.md`

## Allowed Files

For this readiness wave only:

- `docs/CURRENT_TASK.md`
- `docs/plans/active/current-plan.md`
- `docs/ANALYST_OBJECT_MODEL.md`
- `docs/specs/0003-data-contracts.md`
- `docs/LLM_ANALYST_PROMPT_PACK.md`
- `docs/mock_data/situational_awareness_brief.example.json`
- `tests/**`
- `packages/core/src/ai_infra_fund_core/contracts/**` only if contract tests require existing contract definitions to be aligned
- `docs/BUILD_LOG.md` only during final integration

## Forbidden Changes

- no runtime feature implementation
- no UI implementation
- no backend route implementation
- no database migrations
- no dependency changes
- no broker integration
- no live order placement
- no execution endpoints
- no execution-like UI controls
- no arbitrary or private-document crawling
- no paid-report scraping
- no unmanaged model calls
- no model names hard-coded in business logic
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, PnL, or recommendation publication decisions
- no DuckDB/Parquet v1 dependency

## Output Contract

The readiness wave must leave the repo with:

- one active task that points future Codex work at the advisory workstation readiness scope
- one active plan that lists agent streams, file ownership, merge order, tests, forbidden changes, and Definition of Done
- canonical object and contract docs aligned with the workstation workflow
- prompt-pack guidance that keeps LLMs inside classify, extract, summarize, review, critique, and explain roles
- architecture policy tests that guard advisory-only, deterministic ownership, model routing, privacy, and storage boundaries
- normalized mock data usable by the next workstation UI tasks

## Acceptance Criteria

- `docs/CURRENT_TASK.md` no longer references the completed crawler/cloud task as the active task.
- `docs/plans/active/current-plan.md` defines the five readiness streams and merge order.
- Object model, prompt-pack, policy-test, and mock-data work remains advisory/reporting-only.
- Private research remains local-only by default.
- Model routing remains governed by `config/model_profiles.yaml`.
- PostgreSQL + pgvector remains the v1 canonical data spine.
- Architecture policy tests pass after final integration.
- No product runtime, UI, backend, migration, dependency, broker, order, or execution surface is added.

## Tests To Add Or Run

Each stream runs targeted tests for its owned files. Final integration runs:

- `./.venv/bin/python -m unittest tests.test_architecture_policy`
- `./.venv/bin/python -m unittest discover -s tests`
- `python3 -m compileall packages services tests`
- `npm run build --prefix apps/web` only if frontend files change
- `npm audit --omit=dev --prefix apps/web` only if frontend or dependency files change
- `git diff --check`

## Definition Of Done

- five readiness streams completed or concrete blockers documented
- file ownership conflicts resolved without reverting unrelated work
- targeted tests from each stream pass
- architecture policy tests pass
- full Python suite passes
- compile check passes
- frontend checks run only if frontend files change
- `docs/BUILD_LOG.md` updated during final integration
- changes committed and pushed by the final integration owner
- no cloud deployment required unless runtime or deploy files change
