# Active Plan

## Current Status

The older five-agent readiness wave has been replaced by the six-agent ai-infra-fund plan. Phases 0 through 6 are represented in the current implementation history: advisory contracts, fixture-backed read models, read-only APIs, API-backed cockpit readiness, configured public-source crawl materialization, governed LLM extraction/review stubs, and outcome-journal foundations.

The current implementation pass covers Phase 7: shared cloud/runtime ops preflight, richer `/ready` checks, redacted runtime status, and worker startup hardening.

Specs remain canonical. This plan is temporary coordination state. If this plan conflicts with a spec, the spec wins.

## Phase Sequence

| Phase | Name | Outcome |
|---|---|---|
| Phase 0 | Contract/read-model freeze | Advisory objects, read models, evidence IDs, model-run IDs, signal-bundle links, deterministic check refs, and readiness semantics are frozen before implementation expands. |
| Phase 1 | Fixture-backed DB analyst loop | PostgreSQL/pgvector-backed fixtures exercise advisory objects, evidence, model runs, and deterministic readiness checks. |
| Phase 2 | Read-only APIs | Advisory read models are exposed through read-only API surfaces with no broker/order/execution capabilities. |
| Phase 3 | API-backed cockpit UI | Daily Trading Cockpit renders API-backed readiness checks with advisory labels, evidence, model-run refs, and deterministic status. |
| Phase 4 | Real public source crawler | Allowed public sources are crawled with provenance, source-policy controls, and no private or paid-report crawling. |
| Phase 5 | LLM analyst extraction/review | LLMs perform bounded extraction, classification, summarization, review, critique, and explanation with profile-based routing and `ModelRun` audit. |
| Phase 6 | Outcome journal/evaluation | Advisory outputs are evaluated against later outcomes without becoming broker, order, execution, or autonomous trading systems. |
| Phase 7 | Cloud runtime hardening | Runtime configuration, secrets, observability, deployment checks, and operational readiness are hardened. |

## Streams

| Stream | Purpose | Owned Files | Tests |
|---|---|---|---|
| Agent 1 - Current task + plan coordination | Keep the active task phase-scoped, replace the five-agent wave, and make six-agent ownership explicit. | `docs/CURRENT_TASK.md`, `docs/plans/active/current-plan.md` | `git diff --check -- docs/CURRENT_TASK.md docs/plans/active/current-plan.md` |
| Agent 2 - Advisory contracts + read models | Freeze object vocabulary, advisory contract shapes, read-model semantics, evidence references, and deterministic boundary language. | `docs/ANALYST_OBJECT_MODEL.md`, `docs/specs/0003-data-contracts.md`, `packages/core/src/ai_infra_fund_core/contracts/**`, `tests/contracts/**` | contract-focused unit tests, data-contract tests, `git diff --check` |
| Agent 3 - Fixture-backed DB analyst loop + read-only APIs | Implement fixture-backed PostgreSQL/pgvector analyst loop and read-only advisory APIs for cockpit readiness. | database/read-model service files, fixture loader files, read-only API route files, API tests under `tests/**` | DB/read-model tests, API tests, architecture policy tests if routes change |
| Agent 4 - API-backed Daily Trading Cockpit | Replace static cockpit reads with read-only API data and visible readiness checks while preserving advisory-only UI guardrails. | `apps/web/**`, UI tests under `tests/**` | cockpit UI tests, control-room UI tests, frontend build, frontend audit if applicable |
| Agent 5 - Public-source crawler + LLM analyst review | Add public-source ingestion and bounded LLM extraction/review with source provenance, private-research policy, model routing, and `ModelRun` audit. | crawler service files, `docs/LLM_ANALYST_PROMPT_PACK.md`, prompt/crawler tests under `tests/**` | crawler policy tests, prompt-pack tests, model-routing/audit tests |
| Agent 6 - Outcome evaluation + cloud hardening + final integration | Add outcome journal/evaluation checks, harden cloud runtime, resolve cross-stream conflicts, update build log, verify, commit, push, and deploy when applicable. | outcome/evaluation files, cloud/runtime files, integration docs, `docs/BUILD_LOG.md` | full Python suite, compile check, frontend checks when touched, deployment validation when applicable |

## Merge Order

1. Agent 1 lands coordination files first.
2. Agent 2 completes Phase 0 contract/read-model freeze.
3. Agent 3 completes Phase 1 fixture-backed DB analyst loop and Phase 2 read-only APIs.
4. Agent 4 completes Phase 3 API-backed Daily Trading Cockpit readiness checks.
5. Agent 5 completes Phase 4 public-source crawler and Phase 5 LLM analyst extraction/review.
6. Agent 6 completes Phase 6 outcome journal/evaluation and Phase 7 cloud runtime hardening.
7. Agent 6 performs final integration, updates `docs/BUILD_LOG.md`, runs verification, commits, pushes, and deploys when credentials and changed files require it.

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
npm run build --prefix apps/web
npm audit --omit=dev --prefix apps/web
git diff --check
git status --short
```

Frontend checks are required when frontend files change. Cloud deployment validation is required when runtime, deployment, API, or frontend behavior changes and credentials are available.

## Definition Of Done

- `docs/CURRENT_TASK.md` points to advisory contracts and API-backed Daily Trading Cockpit readiness checks.
- Six agent streams are complete or concrete blockers are documented.
- Phases 0 through 7 are complete in order or explicitly deferred with rationale.
- File ownership conflicts are resolved without reverting unrelated work.
- Object model, contract docs, read-only APIs, cockpit UI, crawler, prompt pack, model-routing audit, outcome evaluation, and cloud runtime agree on the same advisory vocabulary.
- Architecture policy tests pass.
- Full Python suite passes.
- Compile check passes.
- Frontend checks pass if frontend files changed.
- `docs/BUILD_LOG.md` is updated during final integration by Agent 6.
- Changes are committed and pushed by the final integration owner.
