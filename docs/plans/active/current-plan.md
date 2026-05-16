# Active Plan

## Current Status

The latest visible shared-thread plan has been reconciled against the repository. The codebase already contains the first product spine the plan requested: contracts, fixture-backed PostgreSQL read models, read-only APIs, API-backed cockpit UI, deterministic configured crawler runtime, LLM extraction/review stubs, outcome-journal foundations, and cloud runtime hardening.

The current coordination pass is harness-only. It updates `docs/CURRENT_TASK.md` and this active plan so future agents do not repeat completed Wave 1 work. The next implementation gate should be scoped separately around governed public-source and LLM analyst extraction/review work.

Specs remain canonical. This plan is temporary coordination state. If this plan conflicts with a spec, the spec wins.

## Phase Sequence

| Phase | Name | Status | Outcome |
|---|---|---|---|
| Phase 0 | Contract/read-model freeze | Complete | Advisory objects, read models, evidence IDs, model-run IDs, signal-bundle links, deterministic check refs, and readiness semantics are represented in docs, contracts, tests, and fixtures. |
| Phase 1 | Fixture-backed DB analyst loop | Complete | PostgreSQL/pgvector-backed fixtures exercise advisory objects, evidence, model runs, run artifacts, and deterministic readiness references. |
| Phase 2 | Read-only APIs | Complete | Advisory read models are exposed through read-only API surfaces with no broker/order/execution capabilities. |
| Phase 3 | API-backed cockpit UI | Complete | Daily Trading Cockpit renders API-backed readiness checks with advisory labels, evidence, model-run refs, and deterministic status. |
| Phase 4 | Real public source crawler | Partial | Deterministic configured-public-source crawler runtime exists; broader source coverage remains a future bounded task. |
| Phase 5 | LLM analyst extraction/review | Partial | Protocol, payload guards, data-class policy, and stubs exist; real model-routed extraction/review remains a future bounded task. |
| Phase 6 | Outcome journal/evaluation | Partial | Outcome journal foundation exists; richer analyst-quality evaluation can expand later. |
| Phase 7 | Cloud runtime hardening | Complete | Runtime configuration, secrets, deployment checks, and cloud readiness validation are hardened. |

## Streams

| Stream | Purpose | Owned Files | Tests |
|---|---|---|---|
| Agent 1 - Current task + plan coordination | Keep the active task phase-scoped and make parallel-agent ownership explicit. | `docs/CURRENT_TASK.md`, `docs/PARALLEL_AGENT_PLAN.md`, `docs/plans/active/current-plan.md` | `git diff --check -- docs/CURRENT_TASK.md docs/PARALLEL_AGENT_PLAN.md docs/plans/active/current-plan.md` |
| Agent 2 - Analyst object model + contracts | Fill missing first-class workstation contracts and keep docs/code/test vocabulary aligned. | `docs/ANALYST_OBJECT_MODEL.md`, `docs/specs/0003-data-contracts.md`, `packages/core/src/ai_infra_fund_core/contracts/**`, `tests/contracts/**`, `tests/test_advisory_workstation_contract_docs.py` | contract-focused unit tests, contract-doc tests, `git diff --check` |
| Agent 3 - LLM analyst prompt pack | Ensure analyst review roles are LLM-mediated, evidence-linked, auditable, and bounded away from deterministic math. | `docs/LLM_ANALYST_PROMPT_PACK.md`, `tests/test_llm_analyst_prompt_pack.py` | prompt-pack tests, architecture policy tests |
| Agent 4 - Architecture policy coverage | Keep advisory-only, no-execution, crawler-source, storage, model-routing, and deterministic/LLM ownership policies enforceable. | `tests/test_architecture_policy.py`, crawler policy docs as needed | architecture policy tests |
| Agent 5 - Mock data normalization | Keep static fixtures consistent with the shared object model and evidence lineage before Wave 2 UI/API work. | `docs/mock_data/**`, `tests/test_situational_awareness_mock_data.py` | mock-data tests |

## Merge Order

1. Agent 1 lands coordination files first.
2. Agent 2 completes object contracts and contract-doc coverage.
3. Agent 5 normalizes mock data if object-model changes require fixture updates.
4. Agent 3 completes LLM analyst prompt-pack coverage.
5. Agent 4 completes architecture policy coverage.
6. Final integration updates `docs/BUILD_LOG.md`, runs verification, commits, and pushes. Cloud deployment is only required when runtime, deployment, API, or frontend behavior changes.

## Forbidden Changes

- no dependency changes
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
- no mutation of another agent's owned files without explicit coordination

## Non-Negotiable Boundaries

- Advisory and reporting only.
- Manual buy/sell entry is local journal/planning only and must not transmit orders.
- LLMs may classify, extract, summarize, review, critique, and explain.
- Deterministic code owns scores, risk, backtests, constraints, target weights, portfolio exposure, entry/exit levels, scenario math, PnL, readiness checks, and publication gates.
- Model routing must use `config/model_profiles.yaml`; business logic must not hard-code model names.
- PostgreSQL + pgvector is the v1 canonical data spine.
- Private research is local-only by default; cloud calls must respect data-class policy.
- Every model call creates a `ModelRun` record.
- Recommendation-like artifacts require advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID where applicable, and deterministic checks.
- Public crawlers must preserve provenance and must not crawl private docs or paid reports.
- APIs are read-only until a later explicitly approved plan changes that boundary; this plan does not approve broker, order, execution, or allocation write surfaces.

## Phase Acceptance Criteria

| Phase | Acceptance Criteria |
|---|---|
| Phase 0 | Contract docs and code contracts agree on advisory object names, required identifiers, evidence refs, model-run refs, deterministic check refs, and readiness semantics. |
| Phase 1 | Fixture-backed PostgreSQL/pgvector loop can load representative advisory/evidence/model-run/readiness data and validate deterministic boundaries. |
| Phase 2 | Read-only APIs expose cockpit-ready advisory read models and architecture policy tests prevent broker/order/execution drift. |
| Phase 3 | Daily Trading Cockpit consumes API data, shows advisory labels/evidence/readiness status, and contains no execution-like controls. |
| Phase 4 | Public crawler uses allowed public sources only, stores provenance, respects source policy, and excludes private docs and paid reports. |
| Phase 5 | LLM analyst flow uses model profiles, records `ModelRun`, handles data-class policy, and cannot own deterministic math or publication gates. |
| Phase 6 | Outcome journal/evaluation records reviewable outcomes and deterministic evaluations without creating autonomous trading behavior. |
| Phase 7 | Cloud runtime validation covers secrets/config, observability, deployment checks, and private-research policy. |

## Verification

Stream owners run their targeted tests. Final integration runs:

```bash
./.venv/bin/python -m unittest tests.test_architecture_policy
./.venv/bin/python -m unittest discover -s tests
python3 -m compileall packages services tests
git diff --check
git status --short
```

Frontend checks are required when frontend files change. Cloud deployment validation is required when runtime, deployment, API, or frontend behavior changes and credentials are available.

## Definition Of Done

- `docs/CURRENT_TASK.md` names one bounded task and does not reopen completed Wave 1 work.
- `docs/PARALLEL_AGENT_PLAN.md` records completed waves and the next candidate gate.
- File ownership conflicts are resolved without reverting unrelated work.
- Object model, contract docs, read-only APIs, cockpit UI, crawler, prompt pack, model-routing audit, outcome evaluation, and cloud runtime agree on the same advisory vocabulary.
- Architecture policy tests pass.
- Targeted verification for the current task passes.
- `docs/BUILD_LOG.md` is updated during final integration.
- Changes are committed and pushed by the final integration owner when implementation changes are made.
