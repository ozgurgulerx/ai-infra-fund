# Build Log

## 2026-05-16 Advisory Workstation Agent A-E Alignment

Implemented the latest Agent A through Agent E plan from the shared planning thread.

- Agent A updated `docs/PRODUCT.md` to reinforce the advisory and reporting-only AI Infrastructure Trading Advisory Workstation boundary, manual-journal-only buy/sell records, and monitored AI infrastructure domains.
- Agent B tightened workstation object contracts so nested advisory payloads reject broker, route, exchange, order, execution, and auto_trade field-like keys.
- Agent B added contract tests covering prohibited execution-style fields on `SourceSignal`, `FinancialSnapshot`, `ValuationContext`, `MacroRegimeSnapshot`, `TradingAdvisory`, and `AdvisoryUpdate`.
- Agent B updated object-model and data-contract docs to restate advisory-only outputs, evidence-linked material claims, scenario-only price targets, planning-only entry/exit levels, and deterministic ownership of PnL, exposure, risk, and accounting.
- Agent C aligned crawler specs 0016/0017 with configured public-source monitoring only, no paid-report scraping, no sensitive private financial document ingestion, no arbitrary unconfigured crawling, and no broker/order/execution/trading-action outputs.
- Agent C confirmed crawler output flow as `SourceFrontier -> SourceSignal -> EvidenceItem -> MarketEvent -> SegmentImpact -> TradingAdvisory candidate update`.
- Agent D updated `docs/UI_SCREEN_SPECS.md` with an advisory/reporting-only workstation UX contract, daily manual decision loop, global UI copy rules, and tighter cockpit/trade-plan/exposure/journal review specs.
- Agent E enriched `docs/mock_data/situational_awareness_brief.example.json` with CEG nuclear restart / power scarcity advisory coverage, including evidence-backed readiness, advisory update, suggested action, price target scenario, planning levels, and open trade plan objects.
- Preserved hard boundaries: no broker integration, no live order placement, no execution endpoint, no execution UI, no automated trading behavior, no dependency changes, and no backend/API/database migration changes.

Verification:

- `./.venv/bin/python -m unittest discover -s tests/contracts` passed, 16 tests.
- `./.venv/bin/python -m unittest tests.test_situational_awareness_mock_data tests.test_advisory_workstation_contract_docs tests.test_architecture_policy` passed, 50 tests.
- `jq empty docs/mock_data/situational_awareness_brief.example.json` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed, 656 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed.
- `git diff --check` passed.

Cloud validation:

- Verified the canonical cloud API health and readiness through the frontend proxy.
- Refreshed the AKS fixture-brief ConfigMap from `docs/mock_data/situational_awareness_brief.example.json`.
- Recreated and completed `job/ai-infra-fund-fixture-advisory`; the job wrote `run-fixture-advisory-249080a9469ca0ab` with 9 source signals, 9 market events, and 8 advisory records.
- Verified the cloud analyst brief and trading-advisory feeds include the new CEG advisory record.
- No cloud image rollout was required because this wave did not change service routes, migrations, Dockerfiles, deployment manifests, or frontend runtime code.

## 2026-05-16 Phase 7 Cloud Runtime Ops Hardening

Implemented the next phase from the shared planning thread: cloud runtime and ops hardening.

- Added shared runtime preflight reporting in `ai_infra_fund_core.runtime.ops`.
- Extended API `/ready` to return a redacted runtime preflight payload while preserving `checks.database` for existing frontend consumers.
- Added advisory/reporting-only and configured-public-source-only boundary status to readiness output.
- Added model-profile, data-directory, production internal-token, database, and crawl user-agent checks.
- Wired worker startup through the same preflight so blocking runtime failures stop the worker before it enters a job loop.
- Updated the containerized deployment spec and active task/plan docs to reflect Phase 7.
- Preserved hard boundaries: no broker integration, no live order placement, no execution endpoint, no execution UI, no automated trading behavior, no new model calls, and no dependency changes.

Verification:

- `./.venv/bin/python -m unittest tests.test_deployment_readiness` passed, 23 tests.
- `python3 -m compileall packages/core/src/ai_infra_fund_core/runtime services/api/src/ai_infra_fund_api/main.py services/worker/src/ai_infra_fund_worker/main.py` passed.
- `./.venv/bin/python -m unittest tests.test_deployment_readiness tests.test_control_room_ui tests.test_architecture_policy` passed, 88 tests.
- `./.venv/bin/python -m unittest tests.test_crawl_scheduler_config tests.test_crawl_advisory_materialization tests.test_outcome_journal_api` passed, 12 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 655 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `git diff --check` passed.

Cloud deployment validation:

- Built and pushed ACR images with tag `26d9367` for API, worker, and web.
- Applied AKS manifest with migration job `ai-infra-fund-migrate-26d9367`.
- Confirmed AKS API and worker deployments are available.
- Confirmed AKS migration and fixture advisory jobs completed.
- Confirmed Azure App Service `ai-infra-fund-frontend` is running `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:26d9367`.
- Verified the public frontend renders the API-backed Daily Trading Cockpit and the proxied API returns healthy, ready, NVDA market-event, analyst-brief, and trading-advisory responses.
- Kept secret values out of command output, docs, and committed files.

## 2026-05-16 Advisory Product Sessions From Shared Plan

Implemented the next feasible sessions from the shared completion plan after the fixture-backed read model.

- Added deterministic crawler materialization from public crawl captures and legacy `signals.equity_events` into canonical `analyst.source_signals` and `analyst.market_events`.
- Added a governed LLM extraction/review boundary with explicit draft object buckets for `EvidenceClaim`, `SourceSignal`, and `MarketEvent`; the v1 implementation remains a no-op stub and rejects scores, weights, constraints, orders, executions, broker concepts, and trade instructions in model-produced draft payloads.
- Added a first-class read-only outcome journal foundation under `analyst.outcome_journal_entries` with advisory links, market-event/evidence lineage, invalidation/risk flags, and deterministic PnL attribution fields.
- Added `GET /internal/outcome-journal/latest` and regenerated `docs/api/openapi.yaml`.
- Extended the Compose smoke gate to verify `analyst.outcome_journal_entries`.
- Preserved hard boundaries: advisory/reporting only, no broker integration, no live order placement, no execution endpoint, no execution UI, no model calls enabled, no LLM-owned scoring, no target-weight generation, and no recommendation-generation changes.

Verification:

- `./.venv/bin/python -m unittest tests.test_crawl_advisory_materialization tests.test_research_extractor_stub tests.test_outcome_journal_migration tests.test_outcome_journal_repository tests.test_outcome_journal_api tests.test_architecture_policy` passed, 46 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 615 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed after fixing the outcome-journal migration foreign-key type from `TEXT` to `UUID`.

Cloud deployment validation:

- Built and pushed ACR images with tag `59e7c33`:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:59e7c33`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:59e7c33`
- Detected and fixed an API image build-target issue during rollout: the first ACR API build used the Dockerfile `test` stage, the new API pod crash-looped running deployment-readiness tests, and the image was rebuilt with explicit `--target runtime`.
- Updated and pushed `deploy/aks-ai-infra-fund.yaml` in commit `62bdbc9` with API, worker, and migration job tag `59e7c33`.
- Applied the AKS rollout in namespace `ai-infra-fund`.
- Completed `job/ai-infra-fund-migrate-59e7c33`; migration output applied `0011_outcome_journal_read_model.sql`.
- Rolled out `deployment/ai-infra-fund-api` and `deployment/ai-infra-fund-worker`.
- Verified cloud endpoints:
  - `http://74.178.223.132/health`
  - `http://74.178.223.132/ready`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/health`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/ready`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/outcome-journal/latest`
- Confirmed cloud API and worker deployments run `aistartuptr.azurecr.io/*:59e7c33`; current API, worker, and PostgreSQL pods are running with zero restarts.

## 2026-05-16 App Diagrams

Added an OpenAI-image-first visual source map for the AI Infrastructure Trading Advisory Workstation.

- Created `docs/APP_DIAGRAMS.md` with layered product, architecture, data lineage, LLM/deterministic boundary, AI infrastructure segment, readiness gate, sequence, UI navigation, API surface, and roadmap views.
- Created `docs/DIAGRAM_STYLE_TEMPLATE.md` with the shared OpenAI diagram style system, palette, prompt scaffold, naming convention, content rules, and review checklist.
- Generated a ten-image OpenAI diagram set under `docs/assets/openai-diagrams/`, using OpenAI image-model bases plus deterministic label compositing for exact repository terminology:
  - `aiw-01-product-operating-loop-openai.png`
  - `aiw-02-runtime-architecture-openai.png`
  - `aiw-03-data-lineage-openai.png`
  - `aiw-04-llm-deterministic-boundary-openai.png`
  - `aiw-05-ai-infrastructure-segment-map-openai.png`
  - `aiw-06-advisory-readiness-gate-openai.png`
  - `aiw-07-daily-brief-sequence-openai.png`
  - `aiw-08-ui-navigation-map-openai.png`
  - `aiw-09-api-surface-openai.png`
  - `aiw-10-build-roadmap-openai.png`
- Updated `README.md` to explain the system gradually from product loop through runtime, lineage, governance, ecosystem, readiness, sequence, UI, API, and roadmap perspectives.
- Kept Mermaid source in `docs/APP_DIAGRAMS.md` for implementation review while removing Mermaid blocks from the README orientation path.
- Updated `docs/PROJECT_MAP.md` to point future developers and Codex agents at the diagram set and style template.
- Removed obsolete diagram assets that were no longer part of the OpenAI diagram pack, including the prior Nano Banana deployment image.
- Preserved hard boundaries: advisory/reporting only, no broker integration, no live order placement, no execution endpoint, no execution UI, manual journal only, and deterministic ownership of accounting, PnL, risk checks, readiness checks, schemas, validation, and audit lineage.
- No application code, backend code, frontend code, dependency, database, broker, order-placement, or execution changes were made.

Verification:

- `git diff --check` passed.

## 2026-05-16 Fixture-Backed Advisory Workstation Read Model

Implemented the first PostgreSQL-backed product loop for the advisory workstation, using fixture evidence instead of live crawling.

- Added `analyst.*` read-model migration tables for source signals, market events, segment impacts, equity impact assessments, valuation contexts, macro regime snapshots, trading advisories, and analyst briefs.
- Added read-only API endpoints for latest source signals, market events, analyst brief, trading advisories, and per-ticker analyst summaries.
- Added a fixture advisory worker command and `scripts/run_fixture_advisory_once.sh` to seed the mocked situational-awareness brief into PostgreSQL with audit/run lineage.
- Updated the Daily Trading Cockpit to load the brief through the backend proxy instead of reading static JSON directly.
- Hardened the server-rendered brief fetch so the page uses the configured internal API base URL and internal token instead of deriving an origin from request headers.
- Hardened the local trade-journal proxy to return structured 400/503 errors for invalid JSON, backend fetch failures, and invalid backend responses.
- Kept the boundary advisory-only: no broker integration, no live order placement, no execution endpoint, no execution UI, no model calls, and no scoring implementation.

Verification:

- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api tests.test_control_room_ui tests.test_architecture_policy tests.test_openapi_export_sync` passed, 59 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 598 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed.
- `scripts/run_fixture_advisory_once.sh` passed and wrote `run-fixture-advisory-00b5b8e7f548033b`.
- `GET /internal/analyst-brief/latest` returned `status=available` and `advisory_label=advisory_only`.
- `GET /internal/trading-advisory/latest` returned advisory-only records with evidence IDs, model run IDs, signal bundle IDs, target weights IDs, and deterministic checks.
- `./.venv/bin/python -m unittest tests.test_control_room_ui tests.test_architecture_policy` passed, 51 tests, after the server-rendered brief fetch hardening.
- `./.venv/bin/python -m unittest discover -s tests` passed, 599 tests, 3 skipped, after the trade-journal proxy hardening.
- `git diff --check` passed.

Cloud deployment validation:

- Built and pushed ACR images with tag `22bd91b`:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:22bd91b`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:22bd91b`
  - `aistartuptr.azurecr.io/ai-infra-fund-web:22bd91b`
- Updated `deploy/aks-ai-infra-fund.yaml` to API/worker tag `22bd91b`.
- Applied AKS rollout in namespace `ai-infra-fund`.
- Recreated and completed release-scoped `job/ai-infra-fund-migrate-22bd91b`; migration output applied `0010_advisory_workstation_read_models.sql`.
- Rolled out `deployment/ai-infra-fund-api` and `deployment/ai-infra-fund-worker`.
- Updated Azure App Service `ai-infra-fund-frontend` to web image tag `22bd91b`, then to `20260516advisoryreadmodel-web` for the server-rendered brief fetch hardening.
- Added and ran `deploy/fixture-advisory-job.yaml` with a temporary fixture ConfigMap; the cloud fixture job wrote `run-fixture-advisory-00b5b8e7f548033b`.
- Verified cloud endpoints:
  - `http://74.178.223.132/health`
  - `http://74.178.223.132/ready`
  - `https://ai-infra-fund-frontend.azurewebsites.net`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/health`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/ready`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/analyst-brief/latest`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/trading-advisory/latest`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/ticker/NVDA/analyst-summary`

## 2026-05-16 Advisory Workstation Contract And Policy Alignment

Aligned the advisory workstation contract/spec layer and added regression tests for the reporting-only boundary.

- Added first-class advisory workstation contract documentation for `SourceSignal`, `FinancialSnapshot`, `ValuationContext`, `MacroRegimeSnapshot`, `TradingAdvisory`, and `AdvisoryUpdate`.
- Updated `docs/specs/0003-data-contracts.md` so the same contracts are canonical in the data-contract spec.
- Added `tests/test_advisory_workstation_contract_docs.py` to keep the object model and data-contract spec aligned.
- Extended architecture policy tests for `TradingAdvisory` advisory-only language, forbidden execution-style fields, crawler no-arbitrary-crawling/no-execution-output boundaries, and deterministic ownership.
- Preserved boundaries: no product code, runtime behavior, database migration, dependency, broker integration, live order placement, execution endpoint, or execution UI changes.

Verification:

- `./.venv/bin/python -m unittest tests.test_advisory_workstation_contract_docs` passed, 4 tests.
- `./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_advisory_workstation_contract_docs` passed, 31 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 584 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `git diff --check` passed.

## 2026-05-16 UI Screen Specs Reframe

Updated `docs/UI_SCREEN_SPECS.md` so the UX matches an advisory/reporting-only trading workstation used daily for manual trading decisions.

- Defined ten primary screens: Daily Trading Cockpit, Live Source Monitoring / Sentiment Radar, AI Infrastructure Segment Map, Ticker Analyst Workbench, Valuation & Price Target Workbench, Trade Plan Workbench, Portfolio Exposure Balancer, Manual Trade Journal + PnL Review, Advisory Update History, and Evidence Library.
- For each screen, specified user question, primary decision supported, data objects, sections, card/table fields, LLM-generated elements, deterministic elements, empty/loading/error states, acceptance criteria, and out-of-scope boundaries.
- Reaffirmed hard UX boundaries: no broker integration, no live trading, no execution UI, no automated trading, manual journal only, evidence-cited advisory insights, scenario-only price targets, and trade-planning-only entry/exit levels.

Verification:

- `git diff --check` passed.
- No app code was modified.

## 2026-05-16 Crawler Advisory Workstation Alignment

Updated crawler specs to align the equity-intelligence crawler with the advisory and reporting-only AI Infrastructure Trading Advisory Workstation.

- Updated `docs/specs/0016-equity-intelligence-crawler.md` to define the crawler as a configured public-source monitor that detects macro, micro, thematic, company, financial, and segment-level changes.
- Added the crawler output flow: `SourceFrontier -> SourceSignal -> EvidenceItem -> MarketEvent -> SegmentImpact -> TradingAdvisory candidate update`.
- Added monitored public-source categories for company investor relations, SEC filings, earnings releases/transcripts, hyperscaler capex commentary, semiconductor supply chain, HBM/memory, CoWoS/advanced packaging, datacenter leasing and power contracts, utility load growth, export controls/geopolitical policy, macro/rates/liquidity commentary, and public sentiment/news flow.
- Updated `docs/specs/0017-crawl-pipeline-runtime.md` to carry the same advisory runtime boundary and prohibited-output rules.
- Preserved hard boundaries: no paid-report scraping, no sensitive private financial document ingestion, no arbitrary unconfigured crawling, no broker/order outputs, no execution outputs, no automated trading actions, and no trade instructions.

Verification:

- `git diff --check` passed.
- No crawler code, backend code, application code, dependency, broker, order-placement, execution, or database changes were made.

## 2026-05-16 Agent Product Boundary

Updated `AGENTS.md` with the product boundary for the AI Infrastructure Trading Advisory Workstation.

- Defined the repo as advisory and reporting-only.
- Allowed trading advisory, thesis updates, valuation context, risk flags, trade plans, and journal reports.
- Reaffirmed that the system must never automate trading or connect to brokers.
- Added the requirement that every implementation improve at least one product-quality area: source monitoring, evidence quality, catalyst detection, segment impact mapping, equity thesis quality, valuation context, risk regime awareness, advisory brief usefulness, trade plan quality, or journal/outcome review quality.
- Added hard-forbidden surfaces: broker credentials, live order placement, order routing, execution endpoints, execution UI, and automated trading loops.

Verification:

- `git diff --check` passed.
- No product code was modified.

## 2026-05-16 Product Reframe

Updated `docs/PRODUCT.md` to frame the product as an advisory and reporting-only AI Infrastructure Trading Advisory Workstation.

- Added the primary product loop from source monitoring through evidence, market events, segment impacts, equity assessment, valuation context, risk updates, trading advisory, briefs, local manual journal, and outcome review.
- Added the core monitored domains across model progress, hyperscaler capex, accelerators, HBM/memory, foundry/CoWoS/semicap, networking, datacenters, power, cooling, sovereign AI/export controls, software monetization, macro liquidity, financials, and valuation.
- Reframed backtesting as outcome review, scenario replay, signal calibration, and thesis-quality evaluation rather than the core product experience.
- Preserved hard boundaries: advisory/reporting only, no broker integration, no live order placement, no automated trading, no execution endpoint, no execution UI, and manual trade journal only.

Verification:

- `git diff --check` passed.
- No application code, backend code, dependency, broker, order-placement, execution, or database changes were made.

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

## 2026-05-16 Advisory Workstation Readiness Wave

Implemented the Agent 1-5 readiness wave for the AI Infrastructure Trading Advisory Workstation.

- Replaced the stale active task with a phase-scoped readiness task covering object-model alignment, LLM prompt boundaries, architecture policy guardrails, and mock-data normalization.
- Updated the active plan with five disjoint agent streams, ownership, merge order, verification commands, and no-cloud-rollout guidance for docs/contracts/test-only work.
- Added bounded workstation contracts for `SourceSignal`, `FinancialSnapshot`, `ValuationContext`, `MacroRegimeSnapshot`, `TradingAdvisory`, `AdvisoryUpdate`, and `OutcomeJournalEntry`.
- Expanded `SegmentImpact` and `EquityImpactAssessment` to carry richer workstation lineage, risk, invalidation, evidence, and model-run fields.
- Added `docs/LLM_ANALYST_PROMPT_PACK.md` with bounded LLM analyst roles, ModelRun audit requirements, data-class policy, and deterministic ownership restrictions.
- Normalized the static advisory mock data with top-level workstation feeds for portfolio snapshot, alerts, suggested actions, journal summary, price scenarios, levels, and correlation exposure.
- Strengthened architecture policy tests for advisory-only boundaries, model-routing discipline, private-research routing, storage discipline, frontend secret exposure, raw secret/private file tracking, and prompt-pack guardrails.
- Preserved boundaries: no UI implementation, backend route, migration, dependency, broker integration, live order placement, execution endpoint, execution UI, unmanaged model call, or LLM-owned scoring/weights/risk/PnL behavior was added.

Verification:

- `./.venv/bin/python -m unittest discover -s tests/contracts` passed, 13 tests.
- `./.venv/bin/python -m unittest tests.test_llm_analyst_prompt_pack` passed, 4 tests.
- `./.venv/bin/python -m unittest tests.test_situational_awareness_mock_data` passed, 5 tests.
- `./.venv/bin/python -m unittest tests.test_advisory_workstation_contract_docs tests.test_architecture_policy` passed, 44 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 643 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `git diff --check` passed.
- Frontend and cloud rollout checks were not required for this scoped wave because no frontend, runtime service, deployment, or dependency files were changed by the staged readiness work.

## 2026-05-16 Wave 2 Advisory Workstation Screens

Implemented the Wave 2 static workstation screens extracted from the shared planning session.

- Replaced the landing page with a Daily Trading Cockpit sourced from `apps/web/lib/situational-awareness/mock-workstation-data.ts`.
- Added the AI Infrastructure Ecosystem Map, Live Market / Sentiment Radar, Ticker Analyst Workbench, Trade Plan Workbench, Manual Trade Intents, and Trade Journal + PnL Review screens.
- Added reusable evidence, risk flag, and advisory-label UI helpers for the workstation screens.
- Kept Wave 2 frontend-only: no backend route, database, crawler, model-router, dependency, broker, order-placement, execution, or live-trading behavior was added.
- Preserved the local journal boundary: manual buy/sell text appears only as local journal record fields, not as order placement or execution controls.

Verification:

- `./.venv/bin/python -m unittest tests.test_wave2_workstation_ui` passed.
- `./.venv/bin/python -m unittest tests.test_control_room_ui` passed.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 40 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 648 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed.
- `git diff --check` passed.

Cloud deployment validation:

- Built and pushed `aistartuptr.azurecr.io/ai-infra-fund-web:e87544c` through ACR.
- Updated Azure App Service `ai-infra-fund-frontend` to `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:e87544c`.
- Verified cloud endpoints:
  - `https://ai-infra-fund-frontend.azurewebsites.net`
  - `https://ai-infra-fund-frontend.azurewebsites.net/radar`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/health`
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/ready`
- Confirmed App Service container config reports `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:e87544c`.

## 2026-05-16 Six-Agent API-Backed Cockpit Alignment

Implemented the next six-agent plan slice from the shared planning session.

- Updated `AGENTS.md` so every analyst evaluation and decision point must be LLM-mediated, evidence-linked, and auditable while preserving deterministic ownership of numeric scores, risk math, constraints, target weights, scenario values, entry/exit levels, PnL, readiness checks, and publication/suppression gates.
- Replaced the older active readiness wave with the six-agent implementation sequence: contract/read-model freeze, fixture-backed DB loop, read-only APIs, API-backed cockpit UI, real public-source crawler, LLM extraction/review, outcome journal/evaluation, and cloud hardening.
- Added `AdvisoryReadinessCheck` and `AnalystBrief` contracts, required readiness checks on `TradingAdvisory`, scenario-key validation, and forbidden broker/order/execution payload-key guards.
- Added the read-only per-ticker endpoint `GET /internal/market-events/{ticker}` and repository support with freshness metadata.
- Switched the Daily Trading Cockpit landing page from static fixture import to API-backed read models, including degraded/stale-data handling for unavailable analyst brief data.
- Preserved advisory-only boundaries: no broker integration, no live order placement, no execution endpoints, no execution UI, no UI-side scoring, no database migration, no dependency change, and no unmanaged model call was added.

Verification:

- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_api tests.test_advisory_workstation_read_model_repository` passed, 8 tests.
- `./.venv/bin/python -m unittest tests.test_control_room_ui tests.test_wave2_workstation_ui` passed, 29 tests.
- `./.venv/bin/python -m unittest discover -s tests/contracts` passed, 15 tests.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 41 tests.
- `./.venv/bin/python -m unittest tests.test_advisory_workstation_contract_docs tests.test_situational_awareness_mock_data` passed, 9 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 652 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed.
- `scripts/run_fixture_advisory_once.sh` passed with run `run-fixture-advisory-b15f2ec40623383b`.
- Development preflight curl against `/internal/market-events/NVDA` returned an available advisory-only ticker event feed.
- Development preflight curl against `/` returned the API-backed Daily Trading Cockpit HTML.
- `git diff --check` passed.

Cloud deployment validation:

- Built and pushed ACR images with tag `26d9367`:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:26d9367`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:26d9367`
  - `aistartuptr.azurecr.io/ai-infra-fund-web:26d9367`
- Applied AKS release manifest for API, worker, PostgreSQL, and migration job `ai-infra-fund-migrate-26d9367`.
- Created the required AKS database/internal-token secret from non-printed values; no secret values were written to logs or docs.
- Confirmed AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` are available.
- Confirmed AKS jobs `ai-infra-fund-migrate-26d9367` and `ai-infra-fund-fixture-advisory` completed.
- Seeded the cloud fixture advisory run with run `run-fixture-advisory-44923d93e5daa5c6`, writing 9 source signals, 9 market events, and 7 advisory records.
- Updated Azure App Service `ai-infra-fund-frontend` to `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:26d9367`.
- Verified cloud endpoints through `https://ai-infra-fund-frontend.azurewebsites.net`:
  - `/api/backend/health` returned `status: ok`.
  - `/api/backend/ready` returned `database: ok`.
  - `/api/backend/internal/market-events/NVDA` returned an available advisory-only ticker event feed.
  - `/api/backend/internal/analyst-brief/latest` returned an available advisory-only brief with 9 market events.
  - `/api/backend/internal/trading-advisory/latest` returned an available advisory-only feed with 7 advisory records.
- Verified the public cockpit HTML renders API-backed content and includes `API read model`, `Advisory-only`, and `No transaction surface`.

## 2026-05-16 Shared Thread Data-Layer Enrichment

Enriched the mock advisory data segment from the accessible shared planning thread and documented the remaining object-model gaps.

- Added fixture-level freshness metadata with `as_of`, `generated_at`, `last_successful_run_id`, object-family freshness, stale-source notes, suppressed reason counts, and suppressed candidate examples.
- Added a valuation data source plan covering company disclosures, market price reference data, public estimate/revision context, macro/rates/liquidity data, and segment catalyst evidence.
- Added explicit LLM analyst role boundaries for source classification, catalyst extraction, segment mapping, equity thesis review, valuation narrative review, risk critique, brief synthesis, and outcome review.
- Added first-class advisory readiness check examples and linked every published mock `trading_advisories` record to a readiness check.
- Enriched `AnalystBrief` with generation timestamp, linked event/segment/risk/action/model-run/readiness IDs, freshness status, stale-source context, suppressed count, and last successful run ID.
- Added missing MSFT and META price target scenarios and entry/exit level sets so every open mock trade plan has matching deterministic planning levels and scenario context.
- Updated `docs/ANALYST_OBJECT_MODEL.md` manual validation counts and mismatch notes to match the current enriched fixture.
- This pass did not modify application code, backend code, frontend code, dependencies, migrations, broker behavior, live order placement, execution endpoints, automated trading behavior, or external transmission behavior.

Verification:

- `jq . docs/mock_data/situational_awareness_brief.example.json` passed.
- `./.venv/bin/python -m unittest tests.test_situational_awareness_mock_data tests.test_advisory_workstation_contract_docs` passed, 9 tests.
- Manual reference check confirmed all `trading_advisories[].readiness_check_ids` resolve and all open trade plan tickers have matching `entry_exit_levels` and `price_target_scenarios`.
