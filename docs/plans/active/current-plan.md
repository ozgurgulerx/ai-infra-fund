# Active Plan

## Current Status

The previous crawler/read-model/cloud-readiness task is complete. The active task is now a readiness wave for the AI Infrastructure Trading Advisory Workstation. This wave prepares the shared object model, prompt boundaries, policy tests, and mock data needed before the next UI and runtime implementation sessions.

Specs remain canonical. This plan is temporary coordination state. If this plan conflicts with a spec, the spec wins.

## Streams

| Stream | Purpose | Owned Files | Tests |
|---|---|---|---|
| Agent 1 - Current task + repo coordination | Keep the active task phase-scoped and make parallel ownership explicit. | `docs/CURRENT_TASK.md`, `docs/plans/active/current-plan.md` | `git diff --check` |
| Agent 2 - Analyst object model + contracts | Align canonical workstation contracts and object language before UI/backend work. | `docs/ANALYST_OBJECT_MODEL.md`, `docs/specs/0003-data-contracts.md`, `packages/core/src/ai_infra_fund_core/contracts/**`, `tests/contracts/**` | contract-focused unit tests, `git diff --check` |
| Agent 3 - LLM analyst prompt pack | Define bounded LLM roles, inputs, outputs, refusal rules, data-class policy, and ModelRun audit requirements. | `docs/LLM_ANALYST_PROMPT_PACK.md`, prompt-pack tests under `tests/**` | prompt-pack documentation tests, architecture policy tests if touched |
| Agent 4 - Architecture policy guardrails | Strengthen tests that prevent broker/order/execution surfaces, LLM-owned deterministic work, hard-coded model names, and storage/privacy drift. | `tests/test_architecture_policy.py`, relevant policy tests under `tests/**` | `./.venv/bin/python -m unittest tests.test_architecture_policy` |
| Agent 5 - Mock-data normalization | Make one stable workstation mock data source for Daily Trading Cockpit and follow-on screen work. | `docs/mock_data/situational_awareness_brief.example.json`, mock-data tests under `tests/**` | mock-data validation tests, `git diff --check` |

## Merge Order

1. Agent 1 lands coordination files first.
2. Agent 2 aligns object model and contracts.
3. Agent 5 normalizes mock data against the object model.
4. Agent 3 adds the prompt pack against the object model and model-routing rules.
5. Agent 4 finalizes policy tests and catches boundary drift.
6. Final integration owner resolves conflicts, updates `docs/BUILD_LOG.md`, runs verification, commits, and pushes.

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
- no arbitrary crawling
- no private-document crawling
- no paid-report scraping
- no unmanaged model calls
- no model names hard-coded in business logic
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, PnL, or recommendation publication decisions
- no DuckDB/Parquet v1 dependency

## Non-Negotiable Boundaries

- Advisory and reporting only.
- Manual buy/sell entry is local journal only and must not transmit orders.
- LLMs may classify, extract, summarize, review, critique, and explain.
- Deterministic code owns scores, risk, backtests, constraints, target weights, portfolio exposure, entry/exit levels, scenario math, PnL, and publication gates.
- Model routing must use `config/model_profiles.yaml`; business logic must not hard-code model names.
- PostgreSQL + pgvector is the v1 canonical data spine.
- Private research is local-only by default; cloud calls must respect data-class policy.
- Every model call creates a `ModelRun` record.
- Recommendation-like artifacts require advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID, and deterministic checks.

## Verification

Stream owners run their targeted tests. Final integration runs:

```bash
./.venv/bin/python -m unittest tests.test_architecture_policy
./.venv/bin/python -m unittest discover -s tests
python3 -m compileall packages services tests
npm run build --prefix apps/web  # only if frontend files change
npm audit --omit=dev --prefix apps/web  # only if frontend or dependency files change
git diff --check
git status --short
```

Cloud deployment validation is required only if runtime or deployment files change. This readiness wave should not require cloud deployment because it is documentation, contract, test, and mock-data alignment work.

## Definition Of Done

- `docs/CURRENT_TASK.md` points to this readiness wave, not the completed crawler/cloud task.
- Five agent streams are complete or concrete blockers are documented.
- File ownership conflicts are resolved without reverting unrelated work.
- Object model, contract docs, prompt pack, policy tests, and mock data agree on the same advisory workstation vocabulary.
- Architecture policy tests pass.
- Full Python suite passes.
- Compile check passes.
- Frontend checks pass if frontend files changed.
- `docs/BUILD_LOG.md` is updated during final integration.
- Changes are committed and pushed by the final integration owner.
