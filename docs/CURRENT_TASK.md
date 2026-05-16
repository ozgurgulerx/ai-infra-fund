# Current Task

## Task

Implement advisory object contracts and API-backed daily cockpit readiness checks.

This task replaces the older five-agent readiness wave with a six-agent implementation plan that moves the AI Infrastructure Trading Advisory Workstation from static/mock readiness toward contract-backed, API-backed, evidence-backed advisory operation.

## Product Objective

Prepare the Daily Trading Cockpit and advisory analyst pipeline for production-shaped use while preserving advisory-only boundaries.

This improves:

- stable advisory object contracts
- fixture-backed database analyst loops
- read-only API surfaces
- API-backed cockpit readiness checks
- public-source intelligence ingestion
- bounded LLM analyst extraction and review
- outcome journal evaluation
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
- `docs/specs/0004-cloud-runtime.md`
- `docs/specs/0005-ui-acceptance.md`
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

Agent 1 may edit only the two coordination docs listed above.

## Allowed Files

The full six-agent implementation may touch only files needed for the phase owned by each agent. Agent-specific ownership is recorded in `docs/plans/active/current-plan.md`.

For this Agent 1 coordination task, allowed files are:

- `docs/CURRENT_TASK.md`
- `docs/plans/active/current-plan.md`

## Forbidden Changes

- no edits outside Agent 1 owned docs for this coordination pass
- no dependency changes
- no product code changes by Agent 1
- no `docs/BUILD_LOG.md` edits by Agent 1
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

- `docs/CURRENT_TASK.md` names the API-backed advisory contracts/cockpit readiness task, not the old five-agent readiness wave or static Wave 2 screen task.
- `docs/plans/active/current-plan.md` defines six agent streams and Phases 0 through 7.
- Contract/read-model freeze happens before API, UI, crawler, LLM, evaluation, or cloud hardening work expands.
- Daily Trading Cockpit readiness checks are read-only, evidence-backed, advisory-labeled, and API-backed by the end of Phase 3.
- All read-only APIs exclude broker/order/execution surfaces.
- PostgreSQL/pgvector remains the canonical v1 data spine.
- Model routing remains profile-based and audited with `ModelRun`.
- Deterministic math boundaries are explicit in docs, contracts, tests, and implementation.
- Private research policy is preserved for crawler, LLM, and cloud runtime work.
- No new dependencies are added.

## Tests To Add Or Run

Agent owners run targeted tests for their phase. Final integration should run:

```bash
./.venv/bin/python -m unittest tests.test_architecture_policy
./.venv/bin/python -m unittest discover -s tests
python3 -m compileall packages services tests
npm run build --prefix apps/web
npm audit --omit=dev --prefix apps/web
git diff --check
git status --short
```

Agent 1 coordination verification:

```bash
git diff --check -- docs/CURRENT_TASK.md docs/plans/active/current-plan.md
```

## Definition Of Done

- Older five-agent readiness wave is replaced with the six-agent plan.
- Phases 0 through 7 are represented in the active plan.
- Agent ownership is explicit enough for parallel work without file conflicts.
- Advisory-only, no broker/order/execution, deterministic math, model routing, PostgreSQL/pgvector, and private-research guardrails are preserved.
- Acceptance criteria and verification commands are documented.
- Agent 1 edits only `docs/CURRENT_TASK.md` and `docs/plans/active/current-plan.md`.
- Final integration owner, not Agent 1, updates `docs/BUILD_LOG.md`, runs full verification, commits, pushes, and deploys where applicable.
