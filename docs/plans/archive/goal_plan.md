# Goal Plan: Using Codex Goals To Keep Implementation Aligned

## Purpose

Use Codex `/goal` as a session-level execution contract for the AI Infrastructure Fund Control Room.

Goals should keep Codex focused on one phase, one bounded outcome, and one verification standard at a time. Goals do not replace specs, tests, reviews, or CI. They make the active Codex session easier to steer and audit.

The core goal rule is:

A Codex goal should name the current phase, the exact artifacts to change, the relevant specs, the required tests, and the definition of done.

## What Goals Are For

Use `/goal` to:

- keep a Codex session focused on one implementation phase
- prevent scope creep
- make spec traceability explicit
- keep verification requirements visible
- track whether the phase objective is actually complete
- optionally set a token budget for bounded tasks

Do not use `/goal` as the only enforcement mechanism. The real controls remain:

- `AGENTS.md`
- specs
- architecture policy tests
- unit/integration/evaluation tests
- subagent review
- CI gates

## Goal Lifecycle

### 1. Start A Phase Goal

Start a goal before implementation begins.

Goal format:

```text
/goal Set the current objective to:
Implement Phase <N>: <phase name> for ai-infra-fund.

Scope:
- Read AGENTS.md.
- Read docs/plans/deployment_harness.md.
- Read <relevant specs>.
- Modify only <allowed paths>.
- Use TDD.
- Run <required tests>.

Definition of done:
- <specific artifacts exist>.
- <specific tests pass>.
- Architecture policy tests pass.
- Spec clauses satisfied are reported.
- Remaining gaps are reported.
```

### 2. Work Against The Goal

During implementation, Codex should periodically check:

- Is the current edit inside the allowed phase?
- Is the work still inside the allowed paths?
- Have failing tests been written first?
- Are implementation choices consistent with the specs?
- Are architecture policy tests still expected to pass?
- Is any new question or spec conflict blocking progress?

### 3. Use Subagents Under The Same Goal

Subagents should receive the active goal in their prompt.

Example:

```text
The active goal is Phase <N>: <phase name>.
Review only the files changed for this goal.
Check against AGENTS.md, relevant specs, and deployment_harness.md.
Report spec drift, missing tests, and critical risks with file references.
Do not broaden scope.
```

### 4. Complete The Goal Only After Verification

Do not mark a goal complete until:

- implementation is done
- tests have run
- architecture policy tests pass
- subagent critical/high findings are fixed or explicitly deferred
- final report includes files changed, tests run, spec clauses satisfied, and remaining gaps

If tests cannot run, the goal is not fully complete. Report the blocker instead.

## Recommended Goal Granularity

Use one goal per phase or subphase.

Good goals:

- Phase 0 governance scaffold
- model profile config and validation
- PostgreSQL + pgvector migrations
- architecture policy tests
- evidence contract schemas
- deterministic target-weight generator
- model router data-class checks
- recommendation artifact audit persistence

Bad goals:

- build the app
- implement the dashboard
- make the trading system work
- add AI
- finish everything

## Phase Goal Templates

### Phase 0: Governance Scaffold

```text
/goal Set the current objective to:
Implement Phase 0 governance scaffold for ai-infra-fund.

Scope:
- Create AGENTS.md.
- Create docs/specs/0001-product-vision.md.
- Create docs/specs/0002-trading-policy.md.
- Create docs/specs/0003-data-contracts.md.
- Create docs/specs/0004-agent-contracts.md.
- Create docs/specs/0005-ui-acceptance.md.
- Create docs/specs/0006-forward-indicators.md.
- Create docs/specs/0007-situational-awareness-thesis-map.md.
- Create docs/specs/0008-model-routing-and-audit.md.
- Create docs/specs/0009-evaluation-harness.md.
- Create docs/specs/0010-repo-patterns-architecture.md.
- Create docs/specs/0011-implementation-roadmap.md.
- Create docs/specs/0012-data-architecture.md.
- Create docs/specs/0013-llm-routing-and-governance.md.
- Create docs/specs/0014-risk-monitoring-and-incidents.md.
- Create docs/specs/0015-containerized-deployment.md.
- Create config/model_profiles.yaml.
- Create tests/test_architecture_policy.py.
- Create Docker Compose scaffold for web, api, worker, postgres, and migrate.
- Do not implement product code, UI, ingestion, scoring, or backtests.

Definition of done:
- Governance files exist.
- Model profiles reflect deployed Foundry models and local fallbacks.
- Architecture policy tests exist.
- Tests run or blockers are reported.
- Spec clauses satisfied and remaining gaps are reported.
```

### Phase 1: Contracts And Schemas

```text
/goal Set the current objective to:
Implement Phase 1 contracts and schemas.

Scope:
- Read AGENTS.md and docs/specs/0003-data-contracts.md.
- Read docs/specs/0008-model-routing-and-audit.md.
- Read docs/specs/0012-data-architecture.md.
- Add tests first for Position, TradeEntry, TradeJournal, UniverseMember, DatasetSnapshot, EvidenceItem, EvidenceClaim, FeatureSet, ModelRun, SignalBundle, TargetWeights, ImplementationEstimate, BacktestRun, ModelInventoryEntry, RecommendationArtifact, RecommendationAudit, IncidentRecord, DataQualityCheck, and RunArtifact.
- Implement only schema/contracts code.

Definition of done:
- Contract tests pass.
- RecommendationArtifact requires advisory label, evidence IDs, model run IDs, signal bundle ID, and target weights ID.
- TargetWeights cannot be created from raw unvalidated LLM output.
- Architecture policy tests pass.
```

### Phase 2: Data Spine

```text
/goal Set the current objective to:
Implement Phase 2 PostgreSQL + pgvector data spine.

Scope:
- Read docs/plans/data_plan.md.
- Read docs/specs/0012-data-architecture.md.
- Add migrations for PostgreSQL + pgvector.
- Add market snapshot, backtest summary, and evaluation summary persistence in PostgreSQL.
- Add tests first for migration, vector query, portfolio snapshot persistence, market snapshot persistence, and backtest/evaluation summary persistence.

Definition of done:
- pgvector extension test passes.
- evidence chunk vector similarity query test passes.
- portfolio snapshot persistence test passes.
- PostgreSQL market snapshot persistence test passes.
- PostgreSQL backtest/evaluation summary persistence test passes.
- storage ownership policy tests pass.
```

### Phase 3: Model Router And ModelRun Ledger

```text
/goal Set the current objective to:
Implement Phase 3 model router and ModelRun ledger.

Scope:
- Read docs/plans/llm_plan.md.
- Read docs/specs/0008-model-routing-and-audit.md.
- Add tests first for model profile loading, task-role resolution, fallback chain, data-class policy, schema validation, and ModelRun persistence.
- Add tests first for prompt version registry and retry policy.
- Implement model router only.

Definition of done:
- model names appear only in config/model_profiles.yaml and tests.
- private_research cloud route is denied by default.
- public_evidence route resolves to an allowed model.
- ModelRun ledger records success and failure metadata.
- deterministic scoring remains independent from LLM availability.
```

### Phase 4: Deterministic Signals And Portfolio

```text
/goal Set the current objective to:
Implement Phase 4 deterministic signals and target-weight generation.

Scope:
- Read docs/specs/0002-trading-policy.md.
- Read docs/specs/0006-forward-indicators.md.
- Add tests first for scoring formulas, formula versions, constraints, and target weights.
- Add tests first for recommendation-versus-trade comparison.
- Do not import model router or LLM clients.

Definition of done:
- signal and portfolio tests pass.
- target weights are reproducible from same inputs.
- no LLM imports exist in signal or portfolio modules.
- architecture policy tests pass.
```

### Phase 5: Evidence Ingestion And Provenance

```text
/goal Set the current objective to:
Implement Phase 5 evidence ingestion and provenance.

Scope:
- Read docs/specs/0003-data-contracts.md.
- Read docs/specs/0012-data-architecture.md.
- Add tests first for source adapters, deterministic parsing, content hashing, chunking, evidence item persistence, local embeddings, provenance, license handling, private report defaults, and data-class routing.
- Implement deterministic parsing and local embeddings first.

Definition of done:
- duplicate content hashes are handled deterministically.
- private reports stay local by default.
- provenance and license handling are enforced.
- evidence claims include source URI, content hash, timestamp, ticker/theme, confidence, and span reference.
- model-assisted extraction creates ModelRun records.
```

### Phase 6: Recommendation Artifacts And Audit

```text
/goal Set the current objective to:
Implement Phase 6 recommendation artifacts and audits.

Scope:
- Read docs/specs/0002-trading-policy.md.
- Read docs/specs/0008-model-routing-and-audit.md.
- Add tests first for recommendation artifact construction, deterministic weight linkage, audit persistence, advisory labels, and evidence/model links.
- LLMs may explain and review only.

Definition of done:
- every recommendation is advisory-only.
- every recommendation references evidence IDs, model run IDs, signal bundle ID, and target weights ID.
- reviewer findings are persisted.
- no LLM can bypass deterministic score or weight generation.
```

### Phase 7: Evaluation Harness

```text
/goal Set the current objective to:
Implement Phase 7 evaluation harness.

Scope:
- Read docs/specs/0009-evaluation-harness.md.
- Add tests first for walk-forward splits, lookahead-bias checks, recursive indicator checks, purged CV and embargo checks, Monte Carlo stress, transaction cost/liquidity/slippage/capacity checks, benchmark comparison, and model benchmark scoring.
- Implement shadow-mode model evaluation without changing production recommendations.

Definition of done:
- benchmark set exists.
- shadow outputs do not affect production recommendations.
- evaluation metrics include schema pass rate, citation accuracy, numeric correctness, contradiction detection, latency, cost, usefulness, transaction cost, liquidity, slippage, and capacity.
- evaluation tests pass.
```

### Phase 8: Local Read-Only UI

```text
/goal Set the current objective to:
Implement Phase 8 read-only local control-room UI.

Scope:
- Read docs/specs/0005-ui-acceptance.md.
- Add UI tests first for portfolio, trade-entry, trade-journal, evidence library, recommendation audit, system architecture / ops room, evaluation, model run status, incident, and data-quality views.
- No order-placement UI.
- No broker integration.

Definition of done:
- UI is read-only and advisory-only.
- Manual trade entry is local journal only.
- recommendation views show evidence links and audit metadata.
- system architecture modules use real test, policy, artifact, health, freshness, or incident records for status colors.
- no live-order or broker controls exist.
- critical UI workflows pass E2E tests.
```

## Budgeting Goals

Use token budgets for bounded work.

Examples:

```text
/goal Set token budget 30000 for Phase 0 governance scaffold.
/goal Set token budget 50000 for Phase 2 data spine.
/goal Set token budget 40000 for Phase 3 model router.
```

If a goal is likely to exceed budget, Codex should stop at a natural checkpoint and report:

- completed work
- remaining work
- tests run
- blockers
- recommended next goal

Do not mark a goal complete just because the budget is nearly exhausted.

## Goal Checkpoints

At meaningful checkpoints, ask Codex to report:

```text
/goal status
Report:
- current objective
- completed substeps
- remaining substeps
- tests run
- deviations from plan
- blockers
```

Use checkpoints after:

- tests are written
- implementation compiles
- policy tests pass
- subagent reviews return
- before final response

## Goal Completion Report

When Codex completes a goal, the final response should include:

```text
Goal completed:
Files changed:
Specs read:
Spec clauses satisfied:
Tests added:
Tests run:
Subagent reviews:
Open gaps:
Next recommended goal:
```

Goal completion should only happen after the objective is genuinely achieved.

## Goal Anti-Patterns

Avoid:

- goals with multiple unrelated phases
- goals without tests
- goals that say "finish the app"
- goals that allow UI before contracts
- goals that allow model names in business logic
- goals that let LLMs compute final scores or weights
- goals that skip architecture policy tests
- goals that treat subagent review as optional for risky changes

## Relationship To Deployment Harness

`deployment_harness.md` defines the full implementation operating model.

This goal plan defines how to use Codex goals inside that operating model.

Use them together:

- `deployment_harness.md` defines phase gates and verification.
- `goal_plan.md` creates a session-level objective for the current phase.
- `AGENTS.md` defines always-on rules.
- specs define acceptance criteria.
- tests enforce behavior.
