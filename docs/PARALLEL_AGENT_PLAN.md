# Parallel Agent Plan

## Purpose

This is the explicit coordination surface for the latest shared planning-thread agent plan. It keeps implementation phase-scoped, prevents overlapping writes, and preserves the advisory-only AI Infrastructure Trading Advisory Workstation boundary.

## Source Of Truth

Always read first:

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/CURRENT_TASK.md`

Then read only the governing specs named by `docs/CURRENT_TASK.md` and `docs/SPEC_ROUTER.md`.

Specs are canonical. Plans are coordination state. If this file conflicts with a spec, the spec wins.

## Current Wave

The latest visible shared-thread plan recommends a six-agent sequence that starts with contracts, fixture-backed persistence, read-only APIs, and API-backed cockpit UI before real public crawling and LLM analyst extraction expand.

The repository is already implemented and verified through the API-backed cockpit foundation:

| Wave | Status | Evidence |
|---|---|---|
| Wave 1 | Complete | Workstation contracts, prompt pack, mock data, and architecture policies are implemented and tested. |
| Wave 2 | Complete | Fixture-backed PostgreSQL analyst loop persists SourceSignal, EvidenceItem, MarketEvent, SegmentImpact, EquityImpactAssessment, ValuationContext, risk regime, TradingAdvisory, AnalystBrief, ModelRun, and RunArtifact read models. |
| Wave 3 | Complete | Read-only advisory workstation APIs exist for latest source signals, market events, analyst brief, trading advisory, and ticker analyst summaries. |
| Wave 4 | Complete | Daily cockpit uses API-backed read models with degraded-state handling. |
| Wave 5 | In progress | First slice promotes risk-regime updates, trade plans, portfolio exposure snapshots, and LLM analyst notes into first-class read models and read-only workstation APIs. |

## Agent Ownership

| Agent | Stream | Owned Files | Output |
|---|---|---|---|
| Agent 1 | Coordination / CURRENT_TASK | `docs/CURRENT_TASK.md`, `docs/PARALLEL_AGENT_PLAN.md`, `docs/plans/active/current-plan.md`, `docs/BUILD_LOG.md` | Current task and merge order stay aligned with the visible plan. |
| Agent 2 | Analyst object model + contracts | `docs/ANALYST_OBJECT_MODEL.md`, `docs/specs/0003-data-contracts.md`, `packages/core/src/ai_infra_fund_core/contracts/**`, `tests/contracts/**`, `tests/test_advisory_workstation_contract_docs.py` | First-class contracts and tests for workstation objects. |
| Agent 3 | LLM analyst prompt pack | `docs/LLM_ANALYST_PROMPT_PACK.md`, `tests/test_llm_analyst_prompt_pack.py` | LLM-mediated analyst review roles with ModelRun audit requirements. |
| Agent 4 | Architecture policy coverage | `tests/test_architecture_policy.py` | Guardrails for advisory-only, no execution, deterministic/LLM boundary, storage, crawler boundaries, and secrets. |
| Agent 5 | Mock data normalization | `docs/mock_data/**`, `tests/test_situational_awareness_mock_data.py` | Static fixture remains consistent with the shared object model and evidence lineage. |

These Wave 1 ownership rows are historical and should not be relaunched unless a future task explicitly reopens Wave 1. New work must create a new current task with disjoint ownership.

## Next Candidate Wave

Wave 5 should be split into smaller tasks before implementation:

1. Daily brief builder/read-model enrichment: first slice covers open trade plans, LLM analyst notes, portfolio exposure, and risk-regime updates; remaining future enrichment includes readiness checks, advisory updates, financial snapshots, PnL summaries, and suggested actions.
2. Real configured public-source coverage: expand source coverage only inside the watchlist/source-registry boundary.
3. Governed LLM analyst extraction/review: use `config/model_profiles.yaml`, create `ModelRun` records, and emit only draft evidence claims, source signals, market events, segment-impact narratives, equity thesis notes, risk critiques, and advisory explanations.
4. Deterministic publication gates: keep scores, risk math, constraints, target weights, entry/exit levels, scenario math, PnL, readiness checks, and publication/suppression decisions deterministic.

## Merge Order

1. Agent 1 coordination.
2. Agent 2 contracts.
3. Agent 5 mock data normalization.
4. Agent 3 prompt pack.
5. Agent 4 architecture policy tests.
6. UI agents one by one after Wave 1 is green.

Do not let two agents write the same file at the same time. If using separate worktrees, merge in the order above.

## Boundary Rule

Do not make everything LLM-owned. Make the system LLM-driven around analysis and deterministic around truth.

LLMs own:

- interpretation
- catalyst extraction
- thesis updates
- risk critique
- narrative
- suggestions

Deterministic code owns:

- PnL
- portfolio exposure
- position weights
- risk-limit checks
- schema validation
- evidence linkage
- timestamps
- scores
- constraints
- target weights
- entry/exit levels
- publication and suppression gates

LLM review cannot bypass failed deterministic checks.

## Forbidden Changes

- no broker integration
- no live order placement
- no execution endpoints
- no execution-like UI controls
- no autonomous trading behavior
- no arbitrary crawling
- no private-document crawling
- no paid-report scraping
- no unmanaged model calls
- no hard-coded model deployment names in business logic
- no LLM-owned scores, weights, constraints, target weights, entry/exit levels, scenario math, PnL, readiness checks, or publication gates
- no DuckDB/Parquet v1 dependency
- no private reports, secrets, `.env`, or `.env.*` commits

## Verification

Wave 1 targeted checks:

```bash
./.venv/bin/python -m unittest tests.contracts.test_advisory_workstation_contracts
./.venv/bin/python -m unittest tests.test_advisory_workstation_contract_docs
./.venv/bin/python -m unittest tests.test_llm_analyst_prompt_pack
./.venv/bin/python -m unittest tests.test_situational_awareness_mock_data
./.venv/bin/python -m unittest tests.test_architecture_policy
python3 -m compileall packages services tests
git diff --check
```

Final integration may additionally run the full Python suite and frontend checks when frontend files change.

## Known Deferred Work

- Some Wave 2 screens are static/mock-backed rather than fully API-backed.
- Real model calls remain governed but mostly stubbed.
- Real public-source crawler expansion remains bounded to configured public sources.
- Cloud rollout is required only when runtime, deployment, API, or frontend behavior changes.
