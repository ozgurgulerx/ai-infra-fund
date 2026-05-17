# Build Log

## 2026-05-17 Ticker Theme Intelligence v1

Implemented live DB-backed ticker/theme intelligence for the ticker analyst workbench.

- Extended the read-only ticker workbench payload with `theme_groups`, including `advisory_stance`, source signals, MarketEvents, impact assessments, LLM notes, trade-plan notes, related ticker rationale, risk flags, invalidation, next watch items, evidence IDs, relevance metadata, and latest availability timestamps.
- Derived `advisory_stance` server-side from the latest stored `TradingAdvisory` and deterministic readiness/suppression state. Stale or suppressed advisory payloads now fall back to `review`/`unrated` stance semantics.
- Added a server-side web adapter for `/internal/ticker/{ticker}/workbench` and updated the ticker page to render live API-backed data instead of `mockWorkstationData`.
- Added ticker workbench tabs for Summary, Themes, News / Events, Notes, Related Tickers, Risks, and Evidence, with advisory-only, readiness/suppression, evidence trace, and degraded/empty states.
- Preserved hard boundaries: no broker integration, no execution UI, no automated trading behavior, no crawler changes, no model calls, and no frontend-computed advisory stance.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.test_ticker_theme_intelligence` failed on missing `theme_groups`, missing live ticker workbench adapter, and missing tabbed ticker page contract.
- `./.venv/bin/python -m unittest tests.test_ticker_theme_intelligence` passed, 4 tests.
- `./.venv/bin/python -m unittest tests.test_ticker_theme_intelligence tests.test_advisory_workstation_read_model_repository tests.test_control_room_ui tests.test_wave2_workstation_ui` passed, 44 tests.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed with 0 vulnerabilities.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 42 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 717 tests, 3 skipped.
- `./.venv/bin/python -m compileall packages services tests` passed.
- `git diff --check` passed.

Cloud deployment validation:

- Pushed implementation commit `01e3e61` (`feat: add ticker theme intelligence workbench`) to `origin/main`.
- Pushed web-copy follow-up commit `7c21cf9` (`fix: remove restricted wording from app shell`) to `origin/main`.
- Built and pushed API image `aistartuptr.azurecr.io/ai-infra-fund-api:01e3e61-runtime` with digest `sha256:e7a096efb3a1fa9a043d3bff0661de935266151f3a5a18472402fc3492578599`.
- Built and pushed web images:
  - `aistartuptr.azurecr.io/ai-infra-fund-web:01e3e61` with digest `sha256:037432b39476c79896157f13bfb14c067e4adc3497cda46cd6cc3cfcc1a9e5bb`.
  - `aistartuptr.azurecr.io/ai-infra-fund-web:7c21cf9` with digest `sha256:d4c8758a8f8a654829a9db15f9b2cf9365b9fe3c9ab70dcbcd15654854f5046d`.
- Rolled AKS deployment `ai-infra-fund-api` in namespace `ai-infra-fund` to `aistartuptr.azurecr.io/ai-infra-fund-api:01e3e61-runtime`; rollout completed and the deployment reported `1/1` ready.
- Updated Azure App Service `ai-infra-fund-frontend` to `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:7c21cf9`; the first public probes hit cold-start timeouts, then the container served successfully.
- Verified cloud endpoints through `https://ai-infra-fund-frontend.azurewebsites.net`:
  - `/api/backend/health` returned `status=ok`.
  - `/api/backend/ready` returned `status=ready`, with `database=ok`, `model_profiles=ok`, `production_internal_token=ok`, `advisory_boundary=ok`, and `source_policy=ok`.
  - `/api/backend/internal/ticker/NVDA/workbench` returned `status=available`, `theme_group_count=6`, first theme `Ai Infrastructure`, first stance `accumulate`, tone `positive`, freshness `current`, 17 evidence IDs, 8 related tickers, 13 risk flags, 10 source signals, 10 MarketEvents, and 3 LLM notes.
  - `/api/backend/internal/ticker/CEG/workbench` returned `status=available`, `theme_group_count=21`, first theme `Ai Infrastructure`, first stance `hold`, tone `neutral`, freshness `current`, 19 evidence IDs, 8 related tickers, 9 risk flags, 7 source signals, 7 MarketEvents, and 4 LLM notes.
- Verified `https://ai-infra-fund-frontend.azurewebsites.net/ticker/NVDA` and `/ticker/CEG` rendered `Ticker Analyst Workbench`, advisory stance, `Summary`, `Themes`, `News / Events`, `Notes`, `Related Tickers`, `Risk watch`, `Evidence trail`, risk chips, and evidence ID pills.
- Confirmed no broker, execution, or order-action UI wording appeared in the final NVDA/CEG ticker HTML.
- Post-copy targeted verification passed:
  - `./.venv/bin/python -m unittest tests.test_control_room_ui tests.test_ticker_theme_intelligence tests.test_trade_journal_ui` passed, 33 tests.
  - `npm run build --prefix apps/web` passed.
  - `npm audit --omit=dev --prefix apps/web` passed with 0 vulnerabilities.
  - `git diff --check -- apps/web/components/app-shell.tsx` passed.

## 2026-05-17 Fallback-Safe Governed Model Client Cloud Rollout

Rolled the governed model-client code path to cloud without enabling real provider calls.

- Pushed `main` through commit `0cd409b` (`feat: support managed identity model auth`), including the governed client commits `8050ce5`, `08434b7`, `9d78b75`, and `0cd409b`.
- Confirmed ACR tags exist for `aistartuptr.azurecr.io/ai-infra-fund-api:0cd409b-runtime` and `aistartuptr.azurecr.io/ai-infra-fund-worker:0cd409b`.
- Confirmed AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` rolled out in namespace `ai-infra-fund` and report `1/1` ready on the `0cd409b` images.
- Corrected the cloud runtime gate to fallback-safe mode: `SHADOW_ANALYST_MODE=fallback`; removed explicit `AI_INFRA_FUND_SHADOW_ANALYST_TASK_ROLE` from the API/worker deployment env so fallback mode does not force a cloud-only analyst role.
- Ran cloud job `ai-infra-fund-daily-brief-0cd409b-fallback` with worker image `aistartuptr.azurecr.io/ai-infra-fund-worker:0cd409b`.
- Cloud daily brief completed with `brief_id=brief-daily-ai-infra-20260517T063758Z-268cb5ec`, `shadow_analyst_status=fallback`, `shadow_draft_count=1`, and `shadow_model_run_count=1`.
- Confirmed no model-provider network path was attempted in fallback mode: latest `audit.model_runs` row for `model-run-e3357db464379c7b494890a2` has `task_role=evidence_summary`, `status=failure`, and `error_summary=shadow analyst model client unavailable in fallback mode`; matching `analyst.shadow_analyst_drafts` row is `ShadowAnalystFallback`.
- Verified cloud API load balancer `/health` returned `status: ok` and `/ready` returned `status: ready` with `database`, `model_profiles`, `production_internal_token`, `advisory_boundary`, and `source_policy` checks ok.
- Verified frontend proxy `/api/backend/internal/analyst-brief/latest` and `/api/backend/internal/trading-advisory/latest` returned HTTP 200 with advisory-only generated data.
- Verified the canonical cockpit page at `https://ai-infra-fund-frontend.azurewebsites.net/` rendered the DB-backed brief `brief-daily-ai-infra-20260517T063758Z-268cb5ec`.

Validation:

- Full Python suite passed: 693 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed from clean deploy worktree.
- `scripts/run_daily_ai_infra_brief_once.sh` passed when rerun against the existing local Compose project; the first isolated-project run only failed because local port `5432` was already allocated by the existing project Postgres container.
- `git diff --check` passed.

## 2026-05-17 Governed Real Shadow Model Client Path

Enabled a real, governed model-client path for the shadow analyst pipeline while preserving deterministic fallback behavior by default.

- Added `ConfiguredModelClient` behind `ai_infra_fund_core.model_routing`, with config-derived route handling for Azure AI Foundry chat completions and local Ollama chat completions.
- Kept model and deployment selection in `config/model_profiles.yaml`; code only resolves task roles and consumes the selected route.
- Added shadow analyst task-role support for `segment_impact_analysis`, `equity_impact_assessment`, `valuation_context_analysis`, `risk_regime_analysis`, `trading_advisory_draft`, and `analyst_brief_draft`.
- Added worker env gating: `SHADOW_ANALYST_MODE=disabled|fallback|real` controls the governed shadow analyst client; default `fallback` preserves the existing unavailable-client fallback. `AI_INFRA_FUND_SHADOW_ANALYST_MODEL_CLIENT=real` remains a compatibility alias, and `AI_INFRA_FUND_SHADOW_ANALYST_TASK_ROLE` can select a shadow analyst role.
- Preserved audit behavior: successful, failed, denied, and fallback attempted paths still flow through `GovernedShadowAnalystPipeline` and `audit.model_runs`; shadow draft rows continue to link through `source_model_run_id`.
- Preserved hard boundaries: no broker/order/execution behavior, no raw LLM publication, no model-owned PnL/accounting/target weights, no private-research cloud calls, no SDK imports, and no frontend changes.

Verification:

- RED checkpoint committed in `8050ce5`: new model-client and worker env tests failed because `ai_infra_fund_core.model_routing.client` did not exist.
- `./.venv/bin/python -m unittest tests.model_routing.test_configured_model_client tests.advisory.test_shadow_analyst_real_model_client` passed, 9 tests.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 41 tests.
- `./.venv/bin/python -m unittest discover -s tests/model_routing` passed, 4 tests.
- `./.venv/bin/python -m unittest discover -s tests/advisory` passed, 11 tests.
- `./.venv/bin/python -m unittest discover -s tests/worker` passed, 8 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 692 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed.
- `scripts/run_daily_ai_infra_brief_once.sh` passed with default fallback mode, producing `shadow_analyst_status=fallback`, `shadow_draft_count=1`, `shadow_model_run_count=1`, and `brief_id=brief-daily-ai-infra-20260517T053319Z-6f722d03`.
- `git diff --check` passed.

Cloud deployment validation:

- Pushed `main` through commit `9d78b75`.
- Built and pushed `aistartuptr.azurecr.io/ai-infra-fund-api:9d78b75-runtime` and `aistartuptr.azurecr.io/ai-infra-fund-worker:9d78b75` through ACR.
- Rolled AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` in namespace `ai-infra-fund`; both reported `1/1` ready.
- Set `SHADOW_ANALYST_MODE=fallback` and `AI_INFRA_FUND_SHADOW_ANALYST_TASK_ROLE=analyst_brief_draft` explicitly on the cloud API/worker deployments.
- Cloud daily brief preflight exposed an older shadow-draft table shape; applied existing migration `0015_shadow_analyst_drafts_contract_repair.sql`, then reran the daily brief successfully.
- Cloud daily brief run produced `shadow_analyst_status=fallback`, `shadow_draft_count=1`, `shadow_model_run_count=1`, and `brief_id=brief-daily-ai-infra-20260517T053802Z-268cb5ec`.
- Cloud frontend proxy `/api/backend/health` returned `status: ok`; `/api/backend/ready` returned `status: ready`, `database: ok`, `model_profiles: ok`, `production_internal_token: ok`, `advisory_boundary: ok`, and `source_policy: ok`.
- Real mode remains deployment-ready but intentionally disabled in cloud until provider endpoint/key configuration is supplied.

## 2026-05-17 Shadow Draft Persistence And Daily Worker Integration

Moved the governed shadow analyst foundation into the live daily advisory workflow.

- Added `analyst.shadow_analyst_drafts` persistence with `draft_type`, `scope`, `ticker`, `source_model_run_id`, `status`, `payload_json`, `evidence_ids`, `validation_errors`, and `created_at`.
- Added idempotent contract migrations so pre-release `model_run_id`/`daily_brief` draft-table shapes are repaired forward to the requested `source_model_run_id` and `daily | ticker` scope contract.
- Added a worker-side shadow draft repository and model-run recorder that do not commit independently, so daily brief generation remains one transaction.
- Updated the governed shadow analyst pipeline to record the `ModelRun` before saving draft rows, preserving database foreign-key lineage.
- Wired `daily_ai_infra_brief_run.py` to build a daily `AnalystContextBundle`, route through `config/model_profiles.yaml`, invoke `GovernedShadowAnalystPipeline`, and persist `review_required`, `rejected`, `fallback`, or denied draft states.
- Kept raw drafts out of published `AnalystBrief` payloads; the brief stores only shadow status/count/model-run metadata and keeps deterministic publication gates in control.
- Preserved hard boundaries: advisory-only, no broker/order/execution behavior, no frontend changes, no real model SDK calls in this slice, no private-research cloud route, no LLM-owned PnL/accounting/target weights, and no direct raw-draft publication.

Verification:

- RED checkpoint committed in `f41363f`: focused tests failed on missing shadow draft repository, migration, daily worker integration, and brief status metadata.
- `./.venv/bin/python -m unittest tests.advisory.test_shadow_analyst_pipeline tests.worker.test_shadow_analyst_draft_repository tests.test_daily_ai_infra_brief_run tests.test_advisory_workstation_read_model_migration tests.test_migration_prefix_uniqueness` passed, 18 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 685 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed.
- `scripts/run_daily_ai_infra_brief_once.sh` passed; the local Compose database reported no pending migrations after the shadow-draft contract repair and produced `shadow_analyst_status=fallback`, `shadow_draft_count=1`, `shadow_model_run_count=1`, and `brief_id=brief-daily-ai-infra-20260517T050515Z-6f722d03`.
- `git diff --check` passed.

## 2026-05-16 Governed Shadow Analyst Pipeline

Implemented the governed LLM shadow analyst foundation for review-required analyst drafts.

- Added `AnalystContextBundle` builders for daily brief and ticker scopes that collect live analyst context from source signals, evidence items, market events, segment impacts, equity impact assessments, valuation context, risk regime updates, portfolio exposure, prior advisories, and outcome journal entries.
- Added non-publishable draft contracts for `SegmentImpactDraft`, `EquityImpactAssessmentDraft`, `ValuationContextDraft`, `RiskRegimeUpdateDraft`, `TradingAdvisoryDraft`, and `AnalystBriefDraft`.
- Added `GovernedShadowAnalystPipeline` that routes through `config/model_profiles.yaml`, records a `ModelRun` for successful, failed, and denied attempts, validates structured output, rejects invalid draft output, denies private-research shadow routing by default, and falls back deterministically when the model client is unavailable.
- Added an optional draft recorder hook so review-required and rejected draft outputs can be stored by worker/API adapters without allowing raw LLM output to publish directly.
- Preserved hard boundaries: no broker integration, no live order placement, no execution behavior, no UI changes, no database migrations, no LLM-owned PnL/accounting/target weights, no unmanaged model calls, and no raw LLM publication path.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.advisory.test_shadow_analyst_pipeline` failed on missing `ai_infra_fund_core.shadow_analyst`.
- GREEN checkpoint: `./.venv/bin/python -m unittest tests.advisory.test_shadow_analyst_pipeline` passed, 6 tests.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 41 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 679 tests, 3 skipped.
- `python3 -m compileall packages/core/src/ai_infra_fund_core/shadow_analyst tests/advisory` passed.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed.
- `git diff --check` passed.

## 2026-05-16 Daily Brief Worker And Source Registry

Implemented the next advisory-workstation phase from the shared planning thread.

- Added a deterministic `daily_ai_infra_brief_run` worker that reads current DB-backed analyst objects, builds readiness-gated `TradingAdvisory` rows, persists an `AnalystBrief`, and records an `audit.run_artifacts` entry.
- Added `scripts/run_daily_ai_infra_brief_once.sh` for the local Compose-backed one-shot worker path.
- Added a configured public-source registry under `config/source_registry.yaml` covering company IR, SEC filings, macro/rates data, semiconductor supply chain sources, datacenter/power sources, AI-progress sources, market data, and public news/sentiment metadata.
- Added `docs/SOURCE_QUALITY_POLICY.md` and `scripts/seed_public_sources.sh` to document and run configured public-source seeding.
- Added source-registry validation and deterministic seed-plan generation that preserves source quality metadata, skips optional-secret sources when credentials are absent, and strips secret placeholders from stored frontier URLs.
- Wired the crawler seed command to use the source registry when present while preserving the legacy watchlist/provider fallback.
- Preserved hard boundaries: advisory/reporting only, configured public sources only, no private-document crawling, no paid-report scraping, no broker integration, no live order placement, no execution endpoint, no execution UI, no unmanaged model calls, no frontend changes, no dependency changes, and no database migration changes.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.test_daily_ai_infra_brief_run` failed on the missing daily brief worker and script.
- RED checkpoint present on local branch: `tests.equity_intelligence.test_source_registry` and `tests.worker.test_source_registry_seed` failed on the missing source registry config and seed wiring.
- GREEN checkpoint: `./.venv/bin/python -m unittest tests.test_daily_ai_infra_brief_run` passed, 4 tests.
- GREEN checkpoint: `./.venv/bin/python -m unittest tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed` passed, 8 tests.
- Combined targeted verification: `./.venv/bin/python -m unittest tests.test_daily_ai_infra_brief_run tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed` passed, 12 tests.
- Policy/crawler verification: `./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_crawl_scheduler_config tests.test_crawl_advisory_materialization` passed, 49 tests.
- `python3 -m compileall packages services tests` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed, 668 tests, 3 skipped.
- `docker compose config` passed.
- First `scripts/seed_public_sources.sh` run exposed a real duplicate-frontier issue caused by canonical `(source_id, url_hash)` collisions; seed-plan de-duplication and source URL template fixes resolved it.
- `scripts/seed_public_sources.sh` passed, logging skipped optional-secret providers `source_fred_macro` and `source_finnhub_company_news` with missing-secret reasons and seeding 34 watched equities, 18 sources, 380 frontier URLs, and 380 queue items.
- A second seed pass reported the same source/frontier counts, and the source-registry frontier row count stayed stable, confirming idempotence.
- `git diff --check` passed.

Cloud deployment validation:

- Built and pushed `aistartuptr.azurecr.io/ai-infra-fund-worker:3d1c154` through ACR.
- Updated AKS deployment `ai-infra-fund-worker` to worker image tag `3d1c154`; rollout completed.
- Executed `python -m ai_infra_fund_worker.crawl seed` inside the cloud worker context.
- Cloud seed logged skipped optional-secret providers `source_fred_macro` and `source_finnhub_company_news` with missing-secret reasons and seeded 34 watched equities, 18 sources, 380 frontier URLs, and 380 queue items.
- Verified cloud health/readiness through the canonical frontend proxy; health returned `status: ok`, readiness returned `status: ready`, `database: ok`, and `source_policy: ok`.

## 2026-05-16 Wave 5 Read-Model Enrichment Slice

Implemented the first bounded Wave 5 enrichment pass after the shared-thread reconciliation.

- Added an additive PostgreSQL migration for first-class `RiskRegimeUpdate`, `TradePlan`, `PortfolioExposureSnapshot`, and `LLMAnalystNote` read models.
- Extended fixture advisory persistence so `risk_regime_updates`, `open_trade_plans`, `portfolio_exposure_snapshot`, and `llm_analyst_notes` are durable read-model rows instead of payload-only fixture data.
- Added read-only advisory repository methods and API routes for:
  - `/internal/segment-map/latest`
  - `/internal/ticker/{ticker}/workbench`
  - `/internal/portfolio/exposure/latest`
- Regenerated `docs/api/openapi.yaml`.
- Updated `docs/CURRENT_TASK.md`, `docs/PARALLEL_AGENT_PLAN.md`, and `docs/plans/active/current-plan.md` to reflect the current implementation slice.
- Preserved hard boundaries: advisory/reporting only, no broker integration, no live order placement, no execution endpoint, no execution UI, no automated trading behavior, no unmanaged model calls, no frontend changes, and no dependency changes.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed` failed on missing Wave 5 tables and fixture persistence; `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api` failed on missing repository methods and routes.
- GREEN checkpoint: `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed` passed, 4 tests.
- GREEN checkpoint: `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api` passed, 11 tests.
- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api` passed, 15 tests.
- `./.venv/bin/python -m unittest tests.test_openapi_export_sync tests.test_architecture_policy tests.test_migration_prefix_uniqueness` passed, 44 tests.
- `python3 -m compileall services/api/src/ai_infra_fund_api services/worker/src/ai_infra_fund_worker tests` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed, 664 tests, 3 skipped.
- `git diff --check` passed.
- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api tests.test_openapi_export_sync` passed, 17 tests.
- `./.venv/bin/python -m unittest tests.test_migration_prefix_uniqueness tests.test_architecture_policy` passed, 42 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 664 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed and applied `0012_wave2_workstation_read_models.sql` in the smoke database.
- `scripts/run_fixture_advisory_once.sh` passed with run `run-fixture-advisory-249080a9469ca0ab`, writing 9 source signals, 9 market events, 8 trade plans, and 8 advisory records.
- `git diff --check` passed.

## 2026-05-16 Six-Agent Plan Reconciliation

Reconciled the latest visible shared-thread six-agent guidance against the current repository state.

- Confirmed the fixture-backed PostgreSQL analyst loop already exists through `services/worker/src/ai_infra_fund_worker/fixture_advisory_run.py`, `services/api/migrations/0010_advisory_workstation_read_models.sql`, and `services/api/src/ai_infra_fund_api/repositories/advisory_workstation.py`.
- Confirmed read-only APIs already expose source signals, market events, latest analyst brief, latest trading advisory, and ticker analyst summaries.
- Confirmed the deterministic configured-public-source crawler runtime and guarded LLM extraction/review stub boundary exist.
- Updated `docs/CURRENT_TASK.md`, `docs/PARALLEL_AGENT_PLAN.md`, and `docs/plans/active/current-plan.md` so future agents do not repeat completed Wave 1 work.
- Identified the next bounded implementation gate as richer daily brief builder/read-model enrichment before governed public-source and LLM analyst extraction/review expansion.
- Recorded the remaining read-model gap: open trade plans, readiness checks, LLM analyst notes, advisory updates, financial snapshots, portfolio exposure, PnL summaries, and suggested actions are still mostly preserved inside fixture payloads rather than first-class builder/read-model outputs.
- No product code, dependencies, migrations, frontend code, backend runtime behavior, broker paths, execution paths, or deployment files were changed.

Verification:

- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api` passed, 12 tests.
- `./.venv/bin/python -m unittest tests.test_research_extractor_stub tests.test_crawl_worker_loop` passed, 9 tests, 2 skipped.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 41 tests.

## 2026-05-16 Wave 1 Parallel-Agent Workstation Alignment

Implemented the latest visible parallel-agent Wave 1 plan from the shared planning thread.

- Added `docs/PARALLEL_AGENT_PLAN.md` as the explicit agent coordination surface with ownership, merge order, LLM/deterministic boundary, forbidden changes, and verification commands.
- Replaced the stale Phase 7 runtime task in `docs/CURRENT_TASK.md` with the current Wave 1 workstation alignment task.
- Updated `docs/plans/active/current-plan.md` so Agent 1 owns the parallel-agent plan and the stale cockpit-readiness DoD wording is removed.
- Added first-class core contracts and tests for `RiskRegimeUpdate`, `TradePlan`, `PortfolioExposureSnapshot`, `PortfolioPosition`, and `LLMAnalystNote`.
- Expanded data-contract docs and contract-doc tests for `SegmentImpact`, `EquityImpactAssessment`, `RiskRegimeUpdate`, `TradePlan`, `PortfolioExposureSnapshot`, `AnalystBrief`, `OutcomeJournalEntry`, and `LLMAnalystNote`.
- Strengthened `docs/LLM_ANALYST_PROMPT_PACK.md` so analyst evaluation and decision points are LLM-mediated, evidence-linked, and auditable while deterministic code owns scores, weights, constraints, levels, exposure, PnL, and gates.
- Added prompt-pack coverage for `fundamental_snapshot_reviewer`, `valuation_context_analyst`, `macro_regime_reviewer`, `portfolio_exposure_explainer`, and `llm_note_reviewer`.
- Tightened architecture policy coverage for the expanded workstation contract set and crawler private/premium-source exclusions.
- Preserved advisory-only and no-execution boundaries. No dependencies, database migrations, backend runtime behavior, frontend behavior, model calls, broker paths, or deployment files were changed.

Verification:

- `./.venv/bin/python -m unittest tests.contracts.test_advisory_workstation_contracts tests.test_advisory_workstation_contract_docs tests.test_llm_analyst_prompt_pack tests.test_situational_awareness_mock_data tests.test_wave2_workstation_ui tests.test_architecture_policy` passed, 73 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 661 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `git diff --check` passed.
- Cloud frontend proxy `/api/backend/health` returned `status: ok`.
- Cloud frontend proxy `/api/backend/ready` returned `status: ready`, `database: ok`, `production_internal_token: ok`, and advisory-only boundaries.

## 2026-05-16 Phase 7 Final Cloud Rollout Follow-Up

Completed the final integration step from the shared planning thread for Phase 7 cloud runtime hardening.

- Confirmed the shared ChatGPT planning thread is still reachable as `ChatGPT - AI Growth Trading System`.
- Built and pushed interim corrected ACR images with tag `20260516workerpreflight` while validating the worker preflight fix:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:20260516workerpreflight`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:20260516workerpreflight`
  - `aistartuptr.azurecr.io/ai-infra-fund-web:20260516workerpreflight`
- Updated `deploy/aks-ai-infra-fund.yaml` and `deploy/fixture-advisory-job.yaml`; final AKS manifests point API and worker workloads at release tag `b573f27`.
- Applied the AKS release manifest to the documented `aks-fund-rag` cluster in namespace `ai-infra-fund`.
- Completed migration job `ai-infra-fund-migrate-20260516workerpreflight`.
- Fixed a production worker readiness regression found during rollout: the worker required `AI_INFRA_FUND_INTERNAL_TOKEN` in production but did not pass the configured-token status into the shared runtime preflight.
- Added regression coverage for production worker startup with and without the internal token.
- Confirmed API and worker deployments run `aistartuptr.azurecr.io/ai-infra-fund-api:b573f27` and `aistartuptr.azurecr.io/ai-infra-fund-worker:b573f27`.
- Tested newer web images on Azure App Service, then restored Azure App Service `ai-infra-fund-frontend` to the known-good image `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:26d9367` after the newer web tags timed out at container startup.
- Updated the frontend App Service `AI_INFRA_FUND_INTERNAL_API_BASE_URL` to the current AKS load balancer endpoint after detecting it still pointed at an older API IP.
- Preserved hard boundaries: advisory/reporting only, no broker integration, no live order placement, no execution endpoint, no execution UI, no automated trading behavior, no unmanaged model calls, and no dependency changes.

Verification:

- `./.venv/bin/python -m unittest tests.test_deployment_readiness` passed, 24 tests.
- `python3 -m compileall services/worker/src/ai_infra_fund_worker/main.py tests/test_deployment_readiness.py` passed.
- `git diff --check` passed.
- Direct AKS API `/health` returned `status: ok`.
- Direct AKS API `/ready` returned `status: ready`, `database: ok`, `production_internal_token: ok`, and `advisory_only: true`.
- AKS API and worker deployments were confirmed healthy on release tag `b573f27`.
- Frontend proxy `/api/backend/health` returned `status: ok`.
- Frontend proxy `/api/backend/ready` returned `status: ready`, `database: ok`, `production_internal_token: ok`, and `advisory_only: true`.
- Frontend proxy `/api/backend/internal/analyst-brief/latest` returned an advisory-only brief with 9 market events after App Service cold-start delay.
- Frontend proxy `/api/backend/internal/trading-advisory/latest` returned 8 advisory-only items.
- Frontend proxy `/api/backend/internal/market-events/NVDA` returned 7 advisory-only NVDA event items.
- Azure App Service was confirmed on the known-good frontend image `DOCKER|aistartuptr.azurecr.io/ai-infra-fund-web:26d9367` with `AI_INFRA_FUND_INTERNAL_API_BASE_URL=http://74.178.223.132`.
- Public cockpit HTML contains `API read model`, `Advisory-only`, and `No transaction surface`.

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
- Fixed worker production preflight so the worker marks `production_internal_token` as configured when `AI_INFRA_FUND_INTERNAL_TOKEN` is provided by the cloud secret, and only requires the crawl user-agent check in crawl mode.
- Preserved hard boundaries: no broker integration, no live order placement, no execution endpoint, no execution UI, no automated trading behavior, no dependency changes, no API route changes, no database migration changes, and no frontend runtime changes.

Verification:

- `./.venv/bin/python -m unittest discover -s tests/contracts` passed, 16 tests.
- `./.venv/bin/python -m unittest tests.test_situational_awareness_mock_data tests.test_advisory_workstation_contract_docs tests.test_architecture_policy` passed, 50 tests.
- `./.venv/bin/python -m unittest tests.test_deployment_readiness` passed, 24 tests.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 41 tests.
- `jq empty docs/mock_data/situational_awareness_brief.example.json` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed, 657 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed, 0 vulnerabilities.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed.
- `git diff --check` passed.

Cloud validation:

- Refreshed the AKS fixture-brief ConfigMap from `docs/mock_data/situational_awareness_brief.example.json`.
- Built and pushed ACR images `aistartuptr.azurecr.io/ai-infra-fund-api:b573f27` and `aistartuptr.azurecr.io/ai-infra-fund-worker:b573f27`.
- Applied AKS manifest with migration job `ai-infra-fund-migrate-b573f27`.
- Fixed the worker cloud rollout after the first new worker pod exposed the missing production-token preflight wiring; the final worker pod passed runtime preflight and entered crawl mode.
- Confirmed AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` are available on image tag `b573f27`.
- Recreated and completed `job/ai-infra-fund-fixture-advisory`; the job wrote `run-fixture-advisory-249080a9469ca0ab` with 9 source signals, 9 market events, and 8 advisory records.
- Verified the canonical cloud API health, readiness, and trading-advisory feeds through the frontend proxy; the trading-advisory feed includes the new CEG advisory record.
- Kept secret values out of docs and final artifacts.

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

## 2026-05-16 Wave 2 Advisory Workstation Read Models

Implemented the next fixture-backed advisory workstation slice from the shared planning thread.

- Added migration `0012_wave2_workstation_read_models.sql` for `analyst.risk_regime_updates`, `analyst.trade_plans`, `analyst.portfolio_exposure_snapshots`, and `analyst.llm_analyst_notes`.
- Extended the fixture advisory worker run so the same deterministic fixture now writes risk regime updates, open trade plans, portfolio exposure snapshots, and audited LLM analyst notes.
- Added read-only repository/API support for:
  - `GET /internal/segment-map/latest`
  - `GET /internal/ticker/{ticker}/workbench`
  - `GET /internal/portfolio/exposure/latest`
- Regenerated `docs/api/openapi.yaml`.
- Preserved advisory-only boundaries: no broker integration, no live order placement, no execution endpoints, no execution UI, no scoring implementation, and no unmanaged model call was added.

Verification:

- RED checkpoint: targeted workstation tests failed before implementation on missing Wave 2 tables, repository methods, and routes.
- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api` passed, 15 tests.
- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api tests.test_openapi_export_sync` passed, 17 tests.
- `./.venv/bin/python -m unittest tests.test_migration_prefix_uniqueness tests.test_architecture_policy` passed, 42 tests.
- `python3 -m compileall packages services tests` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed, 664 tests, 3 skipped.
- `docker compose config` passed.
- `scripts/compose_smoke.sh` passed and applied migration `0012_wave2_workstation_read_models.sql`.
- `scripts/run_fixture_advisory_once.sh` passed with run `run-fixture-advisory-249080a9469ca0ab`, writing 9 source signals, 9 market events, 8 trade plans, and 8 advisory records.
- `git diff --check` passed.

Cloud deployment validation:

- Built and pushed ACR images with tag `7765fa5`:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:7765fa5`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:7765fa5`
- Applied AKS release manifest for API, worker, PostgreSQL, and migration job `ai-infra-fund-migrate-7765fa5`.
- Confirmed AKS migration job `ai-infra-fund-migrate-7765fa5` completed.
- Confirmed AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` rolled out.
- Refreshed the cloud fixture ConfigMap from `docs/mock_data/situational_awareness_brief.example.json`.
- Confirmed AKS fixture job `ai-infra-fund-fixture-advisory` completed with run `run-fixture-advisory-249080a9469ca0ab`, writing 9 source signals, 9 market events, 8 trade plans, and 8 advisory records.
- Verified cloud endpoints through `https://ai-infra-fund-frontend.azurewebsites.net`:
  - `/api/backend/health` returned `status: ok`.
  - `/api/backend/ready` returned `status: ready` with `database: ok`.
  - `/api/backend/internal/segment-map/latest` returned an available advisory-only segment map with risk regime updates.
  - `/api/backend/internal/ticker/NVDA/workbench` returned an available advisory-only ticker workbench with source signals, events, trade plans, risk updates, and LLM analyst notes.
  - `/api/backend/internal/portfolio/exposure/latest` returned an available advisory-only portfolio exposure snapshot.

## 2026-05-16 v1 DB-Backed Advisory Loop Completion

Finalized the v1 DB-backed advisory loop without adding product features, contracts, source categories, model-router changes, real LLM calls, or broker/order/execution behavior.

- Confirmed `origin/main` was up to date at deployed commit `3d1c154`.
- Built and pushed the missing API image tag:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:3d1c154`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:3d1c154` already existed in ACR.
- Rolled AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` to image tag `3d1c154`.
- Did not run migrations; the v1 source registry and daily brief commits did not add migration files.
- Ran cloud source registry seed job `ai-infra-fund-source-seed-3d1c154`.
  - Skipped `source_fred_macro` because `FRED_API_KEY` is not configured.
  - Skipped `source_finnhub_company_news` because `FINNHUB_API_KEY` is not configured.
  - Seeded 34 equities, 18 sources, 380 frontier URLs, and 380 queue items.
- Ran cloud crawler job `ai-infra-fund-crawl-once-3d1c154`.
  - Leased 5 seeded frontier items.
  - Completed with 1 succeeded, 0 not modified, and 4 failed remote-source responses.
- Ran cloud daily brief job `ai-infra-fund-daily-brief-3d1c154`.
  - Run ID: `run-daily-ai-infra-brief-664c3a997f706eb7`.
  - Brief ID: `brief-daily-ai-infra-20260516T195555Z-664c3a99`.
  - Published 18 advisory-only trading advisories.
  - Suppressed 4 candidates through deterministic gates.
- Verified direct cloud API endpoints through `http://74.178.223.132`:
  - `/health` returned `200`.
  - `/ready` returned `200`.
  - `/internal/source-signals/latest` returned `200`, `status=available`, 10 latest items.
  - `/internal/market-events/latest` returned `200`, `status=available`, 10 latest items.
  - `/internal/analyst-brief/latest` returned `200`, `status=available`, brief `brief-daily-ai-infra-20260516T195555Z-664c3a99`, 25 market events, 8 segment impacts, and 18 trading advisories.
  - `/internal/trading-advisory/latest` returned `200`, `status=available`, 10 latest items.
  - `/internal/segment-map/latest` returned `200`, `status=available`, 8 segment impacts, 9 linked market events, and 5 risk regime updates.
  - `/internal/ticker/NVDA/workbench` returned `200`, `status=available`, with source signals, market events, segment impacts, valuation context, trading advisory, trade plan, risk updates, and LLM analyst notes.
  - `/internal/portfolio/exposure/latest` returned `200`, `status=available`, snapshot `pexp_20260516_ai_infra_core`.
- Verified the hosted cockpit at `https://ai-infra-fund-frontend.azurewebsites.net` rendered the generated DB-backed brief `brief-daily-ai-infra-20260516T195555Z-664c3a99`, 25 MarketEvents, 18 suggested advisory actions, and advisory-only/no transaction surface labels.

Verification:

- `./.venv/bin/python -m unittest discover -s tests` passed, 668 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed with 0 vulnerabilities.
- `docker compose config` passed.
- `git diff --check` passed before cloud deployment and after this build log update.

Remaining v1.1 items:

- Improve source-specific extraction quality for public search/API pages that currently produce low-signal titles such as raw JSON snippets or provider messages.
- Configure optional public-data secrets if FRED and Finnhub sources should participate in seeded cloud ingestion.
- Tune source registry URLs that returned remote 403/404 responses during the bounded crawler pass.

## 2026-05-16 Live Crawler Materialization Hardening

Hardened the configured public-source crawler loop so successful live captures
materialize durable `EvidenceItem` rows and link downstream `EquityEvent`,
`SourceSignal`, and `MarketEvent` records to the same evidence ID.

- Added worker-side EvidenceItem persistence for successful configured public
  captures.
- Preserved deterministic event extraction and no-model-call behavior.
- Linked each extracted crawl event to the capture EvidenceItem before
  materializing analyst read-model records.
- Added deterministic JSON article-list extraction for public API captures.
- Suppressed provider error pages and generic search-result pages from becoming
  MarketEvents.
- Added `scripts/crawl_materialization_smoke.sh` with specific diagnostics for:
  - frontier seeded but not leased,
  - leases acquired but fetch failed,
  - captures written but no evidence item,
  - evidence item written but no source signal,
  - source signal written but no MarketEvent.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.worker.test_crawl_materialization_loop` failed on missing evidence repository injection and missing smoke script.
- `./.venv/bin/python -m unittest tests.worker.test_crawl_materialization_loop` passed, 4 tests.
- `./.venv/bin/python -m unittest tests.test_crawl_extraction tests.test_event_extractor_deterministic tests.worker.test_crawl_materialization_loop` passed, 20 tests.
- `./.venv/bin/python -m unittest tests.test_crawl_advisory_materialization tests.test_crawl_worker_loop tests.worker.test_crawl_materialization_loop` passed, 10 tests, 2 skipped.
- `./.venv/bin/python -m unittest tests.test_architecture_policy tests.worker.test_crawl_materialization_loop` passed, 45 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 672 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed.
- `scripts/seed_public_sources.sh` passed locally, seeding 34 equities, 18 active sources, 312 frontier URLs, and 312 queue items; EIA/FRED/Finnhub skipped cleanly due missing optional secrets.
- `docker compose run --rm worker python -m ai_infra_fund_worker.crawl run --once --batch-size 20 --domain-cap 2` passed locally with 20 leased, 11 succeeded, 0 not modified, and 9 failed remote-source responses.
- `scripts/crawl_materialization_smoke.sh` passed locally with nonzero frontier, queue, crawl log, raw capture, EvidenceItem, SourceSignal, and MarketEvent counts.
- `git diff --check` passed.

Cloud deployment validation:

- Runtime commit `50b7d3b` was already on `origin/main` with the crawler hardening changes.
- Built and pushed `aistartuptr.azurecr.io/ai-infra-fund-worker:a8c6f45`; the active AKS worker deployment remained on runtime image `aistartuptr.azurecr.io/ai-infra-fund-worker:50b7d3b`, which contains the same crawler code changes.
- Confirmed AKS worker deployment `ai-infra-fund-worker` rolled out successfully.
- Ran cloud source seed through the worker pod:
  - skipped `source_eia_electricity` because `EIA_API_KEY` is not configured,
  - skipped `source_fred_macro` because `FRED_API_KEY` is not configured,
  - skipped `source_finnhub_company_news` because `FINNHUB_API_KEY` is not configured,
  - seeded 34 equities, 18 active sources, 312 frontier URLs, and 312 queue items.
- Ran cloud crawler once with `--batch-size 20 --domain-cap 2`.
  - leased 20 configured public-source rows,
  - succeeded on 2 captures,
  - failed 18 remote-source responses with logged HTTP 403/429/500 style outcomes,
  - made no model calls.
- Verified cloud database totals:
  - `source_frontier_urls=415`,
  - `crawl_queue_items=415`,
  - `crawl_logs=782`,
  - `source_raw_captures=195`,
  - `evidence_items=66`,
  - `source_signals=203`,
  - `market_events=203`.
- Verified recent cloud materialization rows had evidence provenance:
  - `recent_crawl_logs=421`,
  - `recent_captures=79`,
  - `recent_evidence_items=42`,
  - `recent_source_signals_with_evidence=53`,
  - `recent_market_events_with_evidence=53`.

Guardrails:

- Advisory-only boundary preserved.
- No broker integration, order placement, execution endpoint, execution UI, model call, paid/private scraping, or arbitrary crawler source was added.

Cloud deployment validation:

- Pushed implementation commit `50b7d3b` to `origin/main`.
- Built and pushed ACR images:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:50b7d3b` with digest `sha256:e02e5945c1c06c2b5ab4ef3af756bf2f28b6e6f19fd304cca24af5a51c5e6533`.
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:50b7d3b` with digest `sha256:1664f6b26fc131a6eab5d9ad7de4c03066cdc14b4910b4c7928ee037dce32b98`.
- Rolled AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` to image tag `50b7d3b`; both reported `1/1` ready.
- Did not run migrations; this pass added no migration files.
- Ran cloud source seed job `ai-infra-fund-source-seed-50b7d3b`.
  - Seeded 34 equities, 18 sources, 312 frontier URLs, and 312 queue items.
  - Skipped `source_eia_electricity` because `EIA_API_KEY` is not configured.
  - Skipped `source_fred_macro` because `FRED_API_KEY` is not configured.
  - Skipped `source_finnhub_company_news` because `FINNHUB_API_KEY` is not configured.
- Ran cloud crawler job `ai-infra-fund-crawl-once-50b7d3b`.
  - Leased 20 seeded frontier items.
  - Completed with 5 succeeded, 0 not modified, and 15 failed remote-source responses.
  - Confirmed the tuned SemiAnalysis URL returned `200`.
  - Remaining remote-source failures were primarily Data Center Dynamics `403` responses plus one GDELT `429`.
- Confirmed the cloud database contains 39 crawler `evidence-capture-*` EvidenceItems; latest `created_at` was `2026-05-16T20:15:05Z`.
- Ran cloud daily brief job `ai-infra-fund-daily-brief-50b7d3b`.
  - Run ID: `run-daily-ai-infra-brief-d098433af034f5f4`.
  - Brief ID: `brief-daily-ai-infra-20260516T201354Z-d098433a`.
  - Published 21 advisory-only trading advisories.
  - Suppressed 1 candidate through deterministic gates.
- Verified cloud endpoints through `https://ai-infra-fund-frontend.azurewebsites.net/api/backend`:
  - `/health` returned `200`.
  - `/ready` returned `200`.
  - `/internal/source-signals/latest` returned `200`.
  - `/internal/market-events/latest` returned `200`.
  - `/internal/analyst-brief/latest` returned `200` and brief `brief-daily-ai-infra-20260516T201354Z-d098433a`.
  - `/internal/trading-advisory/latest` returned `200`.
  - `/internal/segment-map/latest` returned `200`.
  - `/internal/ticker/NVDA/workbench` returned `200`.
  - `/internal/portfolio/exposure/latest` returned `200`.
- Verified the hosted cockpit at `https://ai-infra-fund-frontend.azurewebsites.net` rendered brief `brief-daily-ai-infra-20260516T201354Z-d098433a`, 25 MarketEvents, 21 suggested advisory actions, evidence-linked labels, and advisory-only/no transaction surface labels.

## 2026-05-16 Remaining Source Pressure Fix

Finished the remaining v1.1 source cleanup items for the configured public crawler.

- Replaced the Data Center Dynamics ticker search source with the public RSS feed `https://www.datacenterdynamics.com/en/rss/`.
- Changed GDELT from per-ticker burst fanout to one static AI-infrastructure query with `maxrecords=25`, `sort=datedesc`, and a 720-minute refresh interval.
- Added deterministic crawler handling for HTTP `429` so the first retry backs off for one hour instead of the generic five-minute failure backoff.
- Added `EIA_API_KEY` to `.env.example` so all optional public-data source secrets are documented with FRED and Finnhub.
- Confirmed the cloud runtime still has no `EIA_API_KEY`, `FRED_API_KEY`, or `FINNHUB_API_KEY` configured; no placeholder secrets were added.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.equity_intelligence.test_source_registry` failed on the blocked DCD search configuration, per-ticker GDELT fanout, and missing `EIA_API_KEY` env example entry.
- RED checkpoint: `./.venv/bin/python -m unittest tests.test_crawl_worker_loop.CrawlProcessOneUnitTests` failed because HTTP `429` still retried after five minutes.
- `./.venv/bin/python -m unittest tests.test_crawl_worker_loop.CrawlProcessOneUnitTests tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed` passed, 15 tests.
- `python3 -m compileall packages/core/src/ai_infra_fund_core/equity_intelligence services/worker/src/ai_infra_fund_worker/crawl tests` passed.
- `./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_crawl_scheduler_config tests.test_crawl_advisory_materialization` passed, 49 tests.
- `./.venv/bin/python -m unittest tests.test_crawl_fetcher tests.test_equity_intelligence_repository tests.test_crawl_worker_loop.CrawlProcessOneUnitTests tests.equity_intelligence.test_source_registry tests.worker.test_source_registry_seed` passed, 33 tests.
- `docker compose config` passed.
- `git diff --check` passed.
- `./.venv/bin/python -m unittest discover -s tests` passed after the concurrent shadow analyst changes landed, 679 tests, 3 skipped.

Cloud deployment validation:

- Pushed runtime commit `e0a7c30` to `origin/main`.
- Built and pushed ACR images:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:e0a7c30` with digest `sha256:3feb38fc64a772b6384a667001846ef583faa06f8d5ef9762ef90e9b479c098f`.
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:e0a7c30` with digest `sha256:52c3ef2b933b43a19f5fd8c5c3711619ac601c6693a10fb82da89e19f0e82536`.
- Rolled AKS deployments `ai-infra-fund-api` and `ai-infra-fund-worker` to image tag `e0a7c30`; both reported `1/1` ready.
- During final validation, a separate shadow-analyst runtime commit `c8c273e` landed and AKS moved both deployments to image tag `c8c273e`; verified that `c8c273e` contains the DCD RSS, low-pressure GDELT, and HTTP `429` backoff fixes from `e0a7c30`.
- Did not run migrations; this pass added no migration files.
- Ran cloud source registry seed through the deployed worker:
  - seeded 34 equities, 18 active sources, 246 frontier URLs, and 246 queue items,
  - skipped `source_eia_electricity` because `EIA_API_KEY` is not configured,
  - skipped `source_fred_macro` because `FRED_API_KEY` is not configured,
  - skipped `source_finnhub_company_news` because `FINNHUB_API_KEY` is not configured.
- Verified cloud crawler behavior after seed:
  - Data Center Dynamics RSS returned `200` and captured one frontier.
  - GDELT made one low-volume request and returned `429`; the frontier moved to retry at `2026-05-16T21:32:39Z`, confirming the one-hour rate-limit backoff.
- Ran cloud daily brief generation through the deployed worker.
  - Run ID: `run-daily-ai-infra-brief-268cb5ec85c9a575`.
  - Brief ID: `brief-daily-ai-infra-20260516T203319Z-268cb5ec`.
  - Published 22 advisory-only trading advisories.
  - Suppressed 0 candidates through deterministic gates.
- Verified cloud endpoints through `https://ai-infra-fund-frontend.azurewebsites.net/api/backend`:
  - `/health` returned `200`.
  - `/ready` returned `200`.
  - `/internal/source-signals/latest` returned `200` with 10 latest items.
  - `/internal/market-events/latest` returned `200` with 10 latest items.
  - `/internal/analyst-brief/latest` returned `200`, `status=available`, brief `brief-daily-ai-infra-20260516T203319Z-268cb5ec`, 25 MarketEvents, 22 trading advisories, and `advisory_only`.
  - `/internal/trading-advisory/latest` returned `200` with 10 latest items.
  - `/internal/segment-map/latest` returned `200`, `status=available`, 8 segment impacts, 9 linked market events, and 5 risk regime updates.
  - `/internal/ticker/NVDA/workbench` returned `200`, `status=available`, 10 source signals, 10 market events, and 3 trading advisories.
  - `/internal/portfolio/exposure/latest` returned `200`, `status=available`, snapshot `pexp_20260516_ai_infra_core`, 22 positions, and `advisory_only`.
- Verified the hosted cockpit HTML rendered brief `brief-daily-ai-infra-20260516T203319Z-268cb5ec`, 25 MarketEvents, 22 suggested advisory actions, evidence-linked labels, and advisory-only/no transaction surface labels.

## 2026-05-17 Shadow Analyst Manual Review Gate

Implemented deterministic quality evaluation and manual acceptance workflow for governed shadow analyst drafts.

- Added pure core draft-quality evaluation for shadow analyst outputs:
  - evidence coverage and evidence ID validity,
  - deterministic claim-to-evidence support heuristic,
  - forbidden execution-language checks,
  - advisory-only framing checks,
  - specificity, ticker/segment coverage, uncertainty, context completeness, rationale usefulness, hallucinated context/ticker detection, and stale evidence blocking.
- Added sanitized publication payload generation for human-accepted drafts.
  - The accepted payload includes `advisory_only`, evidence IDs, source `ModelRun` ID, quality score, evaluator findings, and readiness checks.
  - Raw draft payload is not blindly copied into publication payloads.
- Added `analyst.shadow_analyst_draft_reviews` migration and indexes.
- Added API repository and internal POST route:
  - `/internal/shadow-analyst/drafts/{draft_id}/review`
  - `accepted_for_publication` is allowed only when deterministic quality checks return `eligible_for_human_review` with no blocking issues.
  - `rejected` and `keep_review_required` decisions are persisted as manual review records.
- Preserved advisory-only boundaries:
  - no broker integration,
  - no live order placement,
  - no execution endpoint or execution UI,
  - no automatic promotion,
  - no LLM-owned scores, target weights, PnL, accounting, or publication gates.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.advisory.test_shadow_analyst_quality` failed on missing `ai_infra_fund_core.shadow_analyst.quality`.
- RED checkpoint: `./.venv/bin/python -m unittest tests.test_shadow_analyst_review_repository tests.test_shadow_analyst_review_api tests.test_advisory_workstation_read_model_migration` failed on missing review repository, route injection, and review migration table.
- `./.venv/bin/python -m unittest tests.advisory.test_shadow_analyst_quality tests.test_shadow_analyst_review_repository tests.test_shadow_analyst_review_api tests.test_advisory_workstation_read_model_migration` passed, 16 tests.
- `./.venv/bin/python -m unittest tests.test_openapi_export_sync tests.test_shadow_analyst_review_api tests.test_shadow_analyst_review_repository tests.advisory.test_shadow_analyst_quality tests.test_advisory_workstation_read_model_migration` passed, 18 tests.
- `./.venv/bin/python -m unittest tests.test_architecture_policy` passed, 42 tests.
- `python3 -m compileall packages services tests` passed.
- `docker compose config` passed.
- `git diff --check` passed.

Known unrelated verification drift in the current worktree:

- `./.venv/bin/python -m unittest discover -s tests` currently fails outside this shadow-review change on ticker-workbench/theme-intelligence tests tied to unrelated modified/untracked frontend/read-model files in the worktree.

Cloud deployment validation:

- Pushed commit `06cd2e6` to `origin/main`.
- Built and pushed ACR images from a clean detached worktree at `06cd2e6`:
  - `aistartuptr.azurecr.io/ai-infra-fund-api:06cd2e6`
  - `aistartuptr.azurecr.io/ai-infra-fund-worker:06cd2e6`
- Ran Kubernetes migration job `ai-infra-fund-migrate-06cd2e6`.
  - Migration log confirmed `Applied migrations: 0016_shadow_analyst_manual_reviews.sql`.
  - Verified `analyst.shadow_analyst_draft_reviews` exists in cloud PostgreSQL.
- Rolled AKS deployments to `06cd2e6`.
  - `ai-infra-fund-api`: `1/1` ready on `aistartuptr.azurecr.io/ai-infra-fund-api:06cd2e6`.
  - `ai-infra-fund-worker`: `1/1` ready on `aistartuptr.azurecr.io/ai-infra-fund-worker:06cd2e6`.
- Verified cloud frontend proxy:
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/health` returned `200`.
  - `https://ai-infra-fund-frontend.azurewebsites.net/api/backend/ready` returned `200`, with advisory boundary, database, model profiles, production internal token, and source policy checks OK.
- Verified new internal shadow-review route on the cloud API with a deliberately invalid payload and redacted internal token.
  - POST `/internal/shadow-analyst/drafts/draft-smoke/review` returned `422 invalid_shadow_draft_review`, confirming the route is deployed and validates payload before touching persistence.

## 2026-05-17 Ticker Workbench Source Display Normalization

Normalized ticker workbench source-signal and MarketEvent display text so raw provider-shaped JSON snippets do not appear in analyst-facing fields.

- Added deterministic source-display normalization in the API read model.
  - Extracts readable title/headline/summary fields from JSON-like provider snippets.
  - Uses `Source captured; summary pending review` when a raw payload has no clean display text.
  - Keeps raw provider payloads in `payload` for provenance/audit while normalizing `why_now`, `what_changed`, source-signal titles/summaries, and MarketEvent display fields.
- Added CEG-like regression fixtures covering:
  - readable title/summary extraction from JSON-like article payloads,
  - safe fallback for URL-only raw provider payloads,
  - evidence ID preservation.

Verification:

- RED checkpoint: `./.venv/bin/python -m unittest tests.test_ticker_theme_intelligence` failed on raw JSON-like `why_now` / `what_changed` display text.
- `./.venv/bin/python -m unittest tests.test_ticker_theme_intelligence` passed, 6 tests.
- `./.venv/bin/python -m unittest discover -s tests` passed, 719 tests, 3 skipped.
- `python3 -m compileall packages services tests` passed.
- `npm run build --prefix apps/web` passed.
- `npm audit --omit=dev --prefix apps/web` passed with 0 vulnerabilities.
- `git diff --check` passed.
