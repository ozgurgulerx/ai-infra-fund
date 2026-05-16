# Harness

## Implementation Loop

1. Read `AGENTS.md`, `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, and `docs/CURRENT_TASK.md`.
2. Use `docs/SPEC_ROUTER.md` to select only the deeper specs named by the current task.
3. Confirm scope, allowed paths, and guardrails before edits.
4. For product code changes, write or update tests first and confirm the intended RED state.
5. Implement the smallest phase-scoped change.
6. Run targeted tests, architecture policy tests, and required verification commands.
7. Report spec traceability, verification, files changed, and remaining gaps.

## TDD Loop

- RED: add or update the test that proves the missing behavior or bug.
- GREEN: implement the minimal change to pass that test.
- REFACTOR: improve structure only after tests are green.
- For docs-only harness changes, RED may be a static checklist or omitted when no product behavior changes.

## Architecture Policy Tests

Policy tests should enforce:

- no live order placement, broker integration, execution endpoints, or execution-like UI controls
- local trade entry remains journal-only
- model names only appear in `config/model_profiles.yaml`, docs, fixtures, or tests
- model calls create `ModelRun` records
- deterministic modules own scores, risk, backtests, constraints, and target weights
- PostgreSQL + pgvector remains the v1 canonical data spine
- DuckDB/Parquet remains future optional only
- UI has no direct database access and no business logic
- private research and secrets are not committed or routed to cloud by default

## Review Protocol

Review every change for:

- spec consistency
- financial-safety regressions
- data-class and privacy violations
- hidden execution or broker surfaces
- missing provenance, audit IDs, or deterministic checks
- migrations and backward compatibility when schemas change
- UI/API boundary drift

If a plan conflicts with a spec, stop and follow the spec. If the spec is ambiguous, record the ambiguity and do not implement beyond the unambiguous boundary.

## Verification Report Format

Use this format in final responses:

```text
Verification:
- Tests:
- Builds/checks:
- Architecture policy:
- Docs/spec trace:

Changed:
- Created:
- Modified:
- Archived:

Guardrails:
- Advisory-only:
- No execution/broker surface:
- Deterministic/LLM boundary:
- Data spine:
- Secrets/private research:

Remaining gaps:
- ...
```

## Phase Gates

- Phase work must name the relevant specs in `docs/CURRENT_TASK.md`.
- No phase is complete until tests and architecture policy checks pass or skipped checks are explicitly justified.
- Recommendation-producing work must prove advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID, and deterministic checks.
- Model-assisted work must prove `ModelRun` persistence and data-class routing.
- UI work must prove no execution controls and no business logic in frontend code.
- Deployment work must prove cloud runtime service boundaries, cloud secret handling, and successful rollout against the canonical Azure deployment target. Local Compose checks are preflight only and must not be reported as deployment readiness.

## Failure Handling

- Test failure: stop feature work, diagnose, and fix or report the blocker.
- Spec conflict: stop implementation, prefer spec over plan, and record the conflict.
- Security/privacy issue: stop, remove exposure, rotate affected secrets if needed, and add a regression test.
- Financial-safety issue: freeze recommendation publication paths until the issue is fixed.
- Migration issue: add a forward-only compatibility migration; do not rewrite applied migrations.
