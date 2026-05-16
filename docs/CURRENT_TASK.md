# Current Task

## Task

Complete Wave 1 parallel-agent alignment for the AI Infrastructure Trading Advisory Workstation.

This task formalizes the latest shared planning-thread guidance, fills missing first-class workstation contracts, tightens LLM analyst prompt coverage, and updates architecture policy coverage before Wave 2 UI/API expansion continues.

## Product Objective

Improve analyst brief usefulness, catalyst interpretation, segment impact mapping, equity thesis quality, risk-regime awareness, and outcome review quality while preserving advisory-only boundaries.

## Governing Docs And Specs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`
- `docs/ANALYST_OBJECT_MODEL.md`
- `docs/LLM_ANALYST_PROMPT_PACK.md`
- `docs/UI_SCREEN_SPECS.md`
- `docs/PARALLEL_AGENT_PLAN.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0004-agent-contracts.md`
- `docs/specs/0008-model-routing-and-audit.md`
- `docs/specs/0016-equity-intelligence-crawler.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`
- `config/model_profiles.yaml`

Specs are canonical. If this task conflicts with a spec, the spec wins.

## Wave 1 Ownership

| Agent | Stream | Owned Scope |
|---|---|---|
| Agent 1 | Coordination / CURRENT_TASK | `docs/CURRENT_TASK.md`, `docs/PARALLEL_AGENT_PLAN.md`, `docs/plans/active/current-plan.md`, `docs/BUILD_LOG.md` |
| Agent 2 | Analyst object model + contracts | `docs/ANALYST_OBJECT_MODEL.md`, `docs/specs/0003-data-contracts.md`, `packages/core/src/ai_infra_fund_core/contracts/**`, contract tests |
| Agent 3 | LLM analyst prompt pack | `docs/LLM_ANALYST_PROMPT_PACK.md`, prompt-pack tests |
| Agent 4 | Architecture policy tests | `tests/test_architecture_policy.py` |
| Agent 5 | Mock data normalization | `docs/mock_data/**`, mock-data tests |

## Allowed Files

- `docs/CURRENT_TASK.md`
- `docs/PARALLEL_AGENT_PLAN.md`
- `docs/plans/active/current-plan.md`
- `docs/BUILD_LOG.md`
- `docs/LLM_ANALYST_PROMPT_PACK.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0016-equity-intelligence-crawler.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`
- `packages/core/src/ai_infra_fund_core/contracts/**`
- `tests/contracts/**`
- `tests/test_advisory_workstation_contract_docs.py`
- `tests/test_llm_analyst_prompt_pack.py`
- `tests/test_situational_awareness_mock_data.py`
- `tests/test_architecture_policy.py`

## Forbidden Changes

- no dependency changes
- no backend runtime changes
- no database migrations
- no frontend changes
- no deployment rollout unless runtime/deploy/frontend behavior changes
- no broker integration
- no live order placement
- no execution endpoints
- no execution-like UI controls
- no autonomous trading behavior
- no arbitrary crawling
- no private-document crawling
- no paid-report scraping
- no unmanaged model calls
- no model names hard-coded in business logic
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, scenario math, PnL, readiness checks, or publication gates
- no DuckDB/Parquet v1 dependency

## Acceptance Criteria

- `docs/PARALLEL_AGENT_PLAN.md` exists and records the latest visible agent ownership and merge order.
- `docs/CURRENT_TASK.md` no longer points at stale Phase 7 cloud runtime work.
- First-class workstation contracts exist for risk regime updates, trade plans, portfolio exposure snapshots, and LLM analyst notes.
- Data-contract docs include the first-class workstation objects used by Wave 2 UI and advisory workflows.
- Prompt pack states that analyst evaluation and decision points are LLM-mediated, evidence-linked, and auditable.
- Prompt pack covers the analyst roles named in the object model.
- Architecture policy tests cover the expanded contract set, crawler private/premium-source boundaries, and deterministic/LLM ownership.
- Advisory-only, no broker/order/execution, deterministic math, model routing, PostgreSQL/pgvector, and private-research guardrails are preserved.

## Tests To Add Or Run

```bash
./.venv/bin/python -m unittest tests.contracts.test_advisory_workstation_contracts
./.venv/bin/python -m unittest tests.test_advisory_workstation_contract_docs
./.venv/bin/python -m unittest tests.test_llm_analyst_prompt_pack
./.venv/bin/python -m unittest tests.test_situational_awareness_mock_data
./.venv/bin/python -m unittest tests.test_architecture_policy
python3 -m compileall packages services tests
git diff --check
```

Final integration may additionally run:

```bash
./.venv/bin/python -m unittest discover -s tests
npm run build --prefix apps/web
npm audit --omit=dev --prefix apps/web
git status --short
```

## Definition Of Done

- Wave 1 alignment artifacts are complete.
- Relevant contract, prompt-pack, mock-data, and architecture policy tests pass.
- Compile check passes.
- `docs/BUILD_LOG.md` records the pass.
- Remaining gaps are documented.
