# Current Task

## Task

Implement Phase 7 cloud runtime and ops hardening for the AI Infrastructure Trading Advisory Workstation.

Earlier passes moved the workstation from static/mock readiness toward contract-backed, API-backed, evidence-backed advisory operation. This pass adds shared runtime preflight checks for cloud deployment readiness and operational status while preserving all advisory-only boundaries.

## Product Objective

Prepare the Daily Trading Cockpit, API, worker, crawler, and advisory analyst pipeline for production-shaped runtime operation while preserving advisory-only boundaries.

This improves:

- redacted runtime readiness reports
- shared API/worker preflight checks
- model-profile configuration checks
- data directory visibility
- production internal-token policy checks
- crawl user-agent contact checks
- advisory-only and configured-source-only boundary visibility
- cloud runtime hardening

## Governing Docs And Specs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`
- `docs/ANALYST_OBJECT_MODEL.md`
- `docs/LLM_ANALYST_PROMPT_PACK.md`
- `docs/UI_SCREEN_SPECS.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0005-ui-acceptance.md`
- `docs/specs/0015-containerized-deployment.md`
- `docs/plans/active/current-plan.md`
- `config/model_profiles.yaml`

Specs are canonical. If this task conflicts with a spec, the spec wins.

## Phase Plan

1. Phase 0 - Contract/read-model freeze
   Freeze advisory object contracts, read-model vocabulary, evidence identifiers, model-run references, signal-bundle references, deterministic check references, and cockpit readiness semantics before runtime implementation expands.

2. Phase 1 - Fixture-backed DB analyst loop
   Build a repeatable fixture-backed PostgreSQL/pgvector analyst loop for advisory objects, evidence links, model runs, and deterministic readiness checks.

3. Phase 2 - Read-only APIs
   Expose advisory read models through read-only APIs. APIs may retrieve, filter, and report advisory state only.

4. Phase 3 - API-backed cockpit UI
   Move the Daily Trading Cockpit from static data to read-only API data while retaining advisory labels, evidence links, deterministic readiness checks, and no execution controls.

5. Phase 4 - Real public source crawler
   Add real public-source crawling for allowed sources only. Respect robots, source terms, rate limits, provenance, and private-research restrictions.

6. Phase 5 - LLM analyst extraction/review
   Add bounded LLM extraction, classification, summarization, review, critique, and explanation flows routed through model profiles and audited with `ModelRun` records.

7. Phase 6 - Outcome journal/evaluation
   Add outcome journal and evaluation loops that compare advisory artifacts against later outcomes without creating broker, order, execution, or autonomous trading behavior.

8. Phase 7 - Cloud runtime hardening
   Harden cloud runtime, observability, secret handling, deployment validation, and operational readiness for the advisory workstation.

## Six-Agent Ownership

| Agent | Stream | Owned Scope |
|---|---|---|
| Agent 1 | Current task + plan coordination | `docs/CURRENT_TASK.md`, `docs/plans/active/current-plan.md` |
| Agent 2 | Advisory contracts + read models | object model docs, data contracts, core contract modules, contract tests |
| Agent 3 | PostgreSQL/pgvector analyst loop + read-only APIs | database/read-model services, fixture loaders, read-only API routes, API tests |
| Agent 4 | API-backed cockpit UI + readiness checks | Daily Trading Cockpit UI, read-only API client, frontend readiness tests |
| Agent 5 | Public-source crawler + LLM analyst review | allowed public crawler, prompt pack alignment, model-run audit tests |
| Agent 6 | Outcome evaluation + cloud hardening + integration | outcome journal, evaluation checks, cloud runtime docs/tests, final integration |

## Allowed Files

The full six-agent implementation may touch only files needed for the phase owned by each agent. Agent-specific ownership is recorded in `docs/plans/active/current-plan.md`.

For this Phase 7 pass, allowed files are:

- shared runtime preflight code under `packages/core/src/ai_infra_fund_core/runtime/`
- API readiness wiring under `services/api/src/ai_infra_fund_api/main.py`
- worker startup readiness wiring under `services/worker/src/ai_infra_fund_worker/main.py`
- deployment/runtime tests under `tests/`
- deployment/runtime docs under `docs/`
- `docs/CURRENT_TASK.md`
- `docs/plans/active/current-plan.md`

## Forbidden Changes

- no dependency changes
- no deployment rollout unless explicitly requested
- no cloud secret reads or secret value logging
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
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, scenario math, PnL, or publication gates
- no DuckDB/Parquet v1 dependency

## Guardrails

- Advisory and reporting only.
- Manual buy/sell entry is local journal/planning only and must not transmit orders.
- LLMs may classify, extract, summarize, review, critique, and explain.
- Deterministic code owns scores, risk, backtests, constraints, target weights, portfolio exposure, entry/exit levels, scenario math, PnL, readiness checks, and publication gates.
- Model routing must use `config/model_profiles.yaml`; business logic must not hard-code model names.
- PostgreSQL + pgvector is the v1 canonical data spine.
- Private research is local-only by default; cloud calls must respect data-class policy.
- Every model call creates a `ModelRun` record.
- Recommendation-like artifacts require advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID where applicable, and deterministic checks.
- Public crawlers must preserve source provenance and must not crawl private docs or paid reports.
- Read-only APIs must not create broker, order, execution, allocation, or autonomous action surfaces.

## Input Contract

Use canonical docs/specs, existing fixture/mock data, and existing test infrastructure. Do not introduce new dependencies for this plan.

## Output Contract

The completed six-agent plan must produce:

- frozen advisory object contracts and read-model semantics
- fixture-backed PostgreSQL/pgvector analyst loop
- read-only advisory APIs
- API-backed Daily Trading Cockpit readiness checks
- public-source crawler with provenance and source-policy controls
- bounded LLM analyst extraction/review with model routing and `ModelRun` audit
- outcome journal/evaluation artifacts
- cloud runtime hardening and verification

## Acceptance Criteria

- `/ready` returns redacted runtime preflight data, not only a database flag.
- `/ready` preserves `checks.database` for existing frontend status consumers.
- Runtime reports include advisory-only and configured-source-only boundaries.
- Runtime reports do not expose database passwords, internal tokens, provider keys, or full secret-bearing connection strings.
- Worker startup uses the shared runtime preflight and fails on blocking checks.
- Crawl mode requires a contactable `SEC_EDGAR_USER_AGENT` when that check is enabled.
- PostgreSQL/pgvector remains the canonical v1 data spine.
- Private research policy is preserved for crawler, LLM, and cloud runtime work.
- No new dependencies are added.

## Tests To Add Or Run

Targeted Phase 7 verification:

```bash
./.venv/bin/python -m unittest tests.test_deployment_readiness
python3 -m compileall packages services tests
git diff --check
```

Final integration may additionally run:

```bash
./.venv/bin/python -m unittest tests.test_architecture_policy
./.venv/bin/python -m unittest discover -s tests
python3 -m compileall packages services tests
npm run build --prefix apps/web
npm audit --omit=dev --prefix apps/web
git diff --check
git status --short
```

## Definition Of Done

- Phase 7 runtime preflight exists in shared core code.
- API and worker both consume the shared preflight.
- `/ready` exposes redacted runtime and advisory-boundary status.
- Runtime failures are blocking only for actual readiness blockers.
- Advisory-only, no broker/order/execution, deterministic math, model routing, PostgreSQL/pgvector, and private-research guardrails are preserved.
- Targeted deployment-readiness tests pass.
- `docs/BUILD_LOG.md` records the runtime hardening pass.
