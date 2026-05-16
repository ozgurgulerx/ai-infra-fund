# Current Task

## Task

Build the fixture-backed advisory workstation read model and API-backed Daily Brief path.

## Product Objective

Make the AI Infrastructure Trading Analyst Workstation visible as a real product loop instead of a static mock.

This improves:

- source monitoring
- catalyst detection
- segment impact mapping
- equity thesis quality
- risk regime awareness
- advisory brief usefulness

## Governing Specs

- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`
- `docs/UI_SCREEN_SPECS.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0016-equity-intelligence-crawler.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`

## Allowed Files

- `apps/web/**`
- `services/api/**`
- `services/worker/**`
- `scripts/**`
- `tests/**`
- `docs/CURRENT_TASK.md`
- `docs/BUILD_LOG.md`
- `docs/api/openapi.yaml`

## Forbidden Changes

- no broker integration
- no live order placement
- no execution endpoints
- no execution UI
- no arbitrary crawling
- no private-document crawling
- no paid-report scraping
- no real model calls
- no scoring ownership transfer to LLMs

## Input Contract

Use `docs/mock_data/situational_awareness_brief.example.json` as a deterministic fixture for the first API-backed product loop.

## Output Contract

Persist and expose this read model:

- `SourceSignal`
- `EvidenceItem`
- `MarketEvent`
- `SegmentImpact`
- `EquityImpactAssessment`
- `ValuationContext`
- `MacroRegimeSnapshot`
- `TradingAdvisory`
- `AnalystBrief`

## Acceptance Criteria

- fixture seed writes PostgreSQL read-model rows idempotently
- read-only APIs expose source signals, market events, latest analyst brief, latest trading advisory, and per-ticker analyst summary
- Daily Brief screen reads API-backed analyst brief data, not local JSON
- every persisted advisory object carries evidence/provenance links where applicable
- no mutation API, broker/order/execution surface, or arbitrary crawler behavior is added
- architecture policy tests pass

## Tests To Add Or Run

- `./.venv/bin/python -m unittest tests.test_advisory_workstation_read_model_migration tests.test_advisory_workstation_fixture_seed tests.test_advisory_workstation_read_model_repository tests.test_advisory_workstation_read_model_api tests.test_control_room_ui`
- `./.venv/bin/python -m unittest tests.test_architecture_policy`
- `npm run build --prefix apps/web`
- `git diff --check`

## Definition Of Done

- implementation complete
- relevant unit/API/UI tests pass
- architecture policy tests pass
- OpenAPI export is synchronized
- `docs/BUILD_LOG.md` updated
- remaining gaps documented
