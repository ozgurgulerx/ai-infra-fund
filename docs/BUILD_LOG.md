# Build Log

## 2026-05-16 Harness Consolidation

Created a smaller agent-followable documentation harness:

- `AGENTS.md` is now a short operational entrypoint.
- `docs/PRODUCT.md`, `docs/ARCHITECTURE.md`, `docs/CURRENT_TASK.md`, `docs/HARNESS.md`, `docs/SPEC_ROUTER.md`, and `docs/DECISIONS.md` are the consolidated control docs.
- Old root plan files were moved to `docs/plans/archive/`.
- `docs/plans/active/current-plan.md` now holds the active plan pointer.

Duplicate content found in old plans:

- advisory-only, no broker, no live order placement, and no execution UI were repeated across plans and specs
- PostgreSQL + pgvector v1 ownership was repeated in data, database, deployment, and harness plans
- DuckDB/Parquet future-only policy was repeated in data architecture plans
- LLM/deterministic boundary and `config/model_profiles.yaml` routing were repeated in LLM/model-routing plans
- TDD, phase gates, architecture policy tests, and verification report requirements were repeated across deployment and spec-driven plans

Conflicting or drift-prone wording found:

- some old plans used "trading system" language; canonical wording is now advisory financial analyst/control-room system
- older phase numbering stopped at local UI, while later specs added crawler/runtime phases; `SPEC_ROUTER.md` now routes by task instead of relying on one phase list
- plans were treated as source material; specs are now explicitly canonical and plans are active-or-archived only

## 2026-05-16 MarketEvent Contract

Implemented the first-class `MarketEvent` contract for catalyst-driven AI infrastructure analysis.

- Added a pure core contract with validated event type, direction, review status, source evidence IDs, tickers, companies, themes, catalyst text, AI relevance, horizon, bounded confidence, point-in-time timestamps, content hash, and optional model run linkage.
- Added focused tests for valid events, invalid event types, missing provenance, missing content hash, missing `available_at`, confidence bounds, point-in-time ordering, and deterministic extraction without model calls.
- Added `MarketEvent` coverage to the Phase 1 contract tests and architecture policy checks for provenance before signal use.
- Preserved advisory-only boundaries: no UI, database migration, model routing implementation, scoring, broker integration, live order placement, or execution surface was added.

Verification:

- `python3 -m unittest tests.test_market_event_contract tests.test_contracts_phase1 tests.test_architecture_policy` passed, 45 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 570 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `git diff --check` passed.
