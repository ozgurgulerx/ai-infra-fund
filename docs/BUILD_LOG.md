# Build Log

## 2026-05-16 Cloud Deployment Gate Clarification

Updated the harness so deployment readiness is validated only against the canonical Azure cloud deployment target.

- `AGENTS.md` now states that local Compose is development preflight only and does not count as deployment validation.
- `docs/HARNESS.md` now requires cloud rollout, cloud service-boundary checks, and cloud secret handling for deployment work.
- `docs/specs/0015-containerized-deployment.md` now separates portable container runtime from the Azure cloud deployment gate.
- `deploy/aks-ai-infra-fund.yaml` now points API and worker workloads to cloud image tag `20260516cloudgate`.

The earlier local Compose smoke result remains useful as preflight, but it is not sufficient for deployment readiness.

Cloud deployment validation:

- Built and pushed ACR images:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:20260516cloudgate`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:20260516cloudgate`
  - `aistartuptr.azurecr.io/ai-infra-fund-web:20260516cloudgate`
- Applied the AKS manifest to namespace `ai-infra-fund`.
- Recreated and completed the AKS migration job.
- Verified AKS API and worker deployments rolled out.
- Updated Azure App Service `ai-infra-fund-frontend` to the new web image.
- Verified cloud endpoints:
  - `http://74.178.223.132/health`
  - `http://74.178.223.132/ready`
  - `https://ai-infra-fund-frontend.azurewebsites.net`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/health`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/ready`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/status/overview`

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

## 2026-05-16 SegmentMap And Equity Impact Contracts

Implemented the scoped SegmentMap/MarketEvent contract layer for the situational-awareness analyst loop.

- Added canonical AI infrastructure `Segment` values and theme aliases for model progress, hyperscaler capex, accelerators, HBM, CoWoS, foundry/equipment, networking, datacenters, power/grid, cooling/electrical infrastructure, sovereign AI/export controls, and software monetization.
- Kept `MarketEvent` as the canonical catalyst contract and added validated segment mapping through its `segments` property.
- Added `SegmentImpact` for first-order and second-order ticker propagation.
- Added `EquityImpactAssessment` with bull case, bear case, risk flags, invalidation, evidence linkage, segment linkage, and bounded confidence.
- Preserved boundaries: no UI, model routing, migrations, scoring, recommendation generation, broker/execution features, or backtesting changes.

Verification:

- `./.venv/bin/python -m unittest tests.contracts.test_segment_market_event_contracts` passed, 6 tests.
- `./.venv/bin/python -m unittest tests.test_market_event_contract tests.test_contracts_phase1 tests.test_architecture_policy` passed, 45 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 576 tests, 3 skipped.
- `python3 -m compileall packages tests/contracts` passed.
- `git diff --check` passed.

## 2026-05-16 Daily Situational Awareness Brief Screen

Implemented the Daily Situational Awareness Brief screen from static mock data.

- Replaced the old landing tiles with a dense analyst-control-room brief sourced from `docs/mock_data/situational_awareness_brief.example.json`.
- Added sections for executive summary, top `MarketEvent`s, segment impacts, equity impact assessments, risk regime updates, evidence references, risk flags, invalidation conditions, and advisory action labels.
- Kept the screen frontend-only and static: no backend endpoint, database, crawler, model-router, scoring, recommendation-generation, broker, order-placement, execution, or backtesting UI changes.
- Updated the web Docker build so the static mock data is available during container builds.

Verification:

- `npm run build --prefix apps/web` passed.
- `./.venv/bin/python -m unittest tests.test_control_room_ui` passed, 20 tests.
- `git diff --check` passed.
- `docs/CURRENT_TASK.md` uses the required `## Governing Specs` harness heading so architecture policy checks can run cleanly.

## 2026-05-16 Analyst Object Model

Created `docs/ANALYST_OBJECT_MODEL.md` from the current trading-workstation UI screen specs and situational-awareness cockpit mock data.

- Defined shared analyst objects for `MarketEvent`, `SegmentImpact`, `EquityImpactAssessment`, `RiskRegimeUpdate`, `TradePlan`, `PortfolioExposureSnapshot`, `AnalystBrief`, `OutcomeJournalEntry`, and `LLMAnalystNote`.
- Captured each object's purpose, fields, required fields, evidence requirements, validation rules, consuming screens, allowed LLM analyst role, and deterministic field ownership.
- Preserved advisory-only boundaries: no broker integration, no live order placement, no execution UI, manual journal only, and deterministic ownership of scores, risk, constraints, target weights, exposure, levels, and PnL.
- Manually validated `docs/mock_data/situational_awareness_brief.example.json` against the model and documented fixture/schema gaps inside the object-model doc.

Validation:

- `jq . docs/mock_data/situational_awareness_brief.example.json` passed.
- Confirmed 19 portfolio positions, 19 open trade plans, 19 price-target scenario sets, and 19 entry/exit level sets for the AI infrastructure ticker set.
- Confirmed linked event IDs, position trade plan IDs, and plan ticker-level scenario/level references resolve within the fixture.
- This object-model update did not modify application code, backend code, dependencies, broker behavior, order-placement surfaces, execution surfaces, or database artifacts.

## 2026-05-16 Trading Cockpit Mock And Commit Validation

Reviewed and validated the combined SegmentMap contract, static Daily Brief UI, UI screen spec, and richer trading cockpit fixture.

- Expanded `docs/mock_data/situational_awareness_brief.example.json` with portfolio snapshot, open trade plans, watchlist alerts, suggested actions, local trade journal summary, deterministic PnL summary, price target scenarios, entry/exit levels, correlation exposures, and LLM analyst notes.
- Covered the AI infrastructure ticker universe: `NVDA`, `AMD`, `AVGO`, `TSM`, `ASML`, `MU`, `ANET`, `MRVL`, `VRT`, `ETN`, `PWR`, `CEG`, `DLR`, `EQIX`, `ORCL`, `MSFT`, `GOOGL`, `AMZN`, and `META`.
- Updated `docs/UI_SCREEN_SPECS.md` with the AI Infrastructure Trading Analyst Workstation loop and advisory/local-journal guardrails.
- Preserved boundaries: advisory-only, no broker integration, no live order placement, no execution UI, no backend behavior change, no database migration, no model-router change, and no UI-side scoring/PnL/target-weight logic.

Verification:

- `jq . docs/mock_data/situational_awareness_brief.example.json` passed.
- `./.venv/bin/python -m unittest tests.contracts.test_segment_market_event_contracts tests.test_market_event_contract tests.test_contracts_phase1 tests.test_control_room_ui tests.test_architecture_policy` passed, 71 tests.
- `npm run build --prefix apps/web` passed.
- `git diff --check` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed, 576 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed.
