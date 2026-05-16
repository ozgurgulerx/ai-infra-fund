# Current Task

## Task

Complete the next advisory-product sessions after the fixture-backed read model:

1. Materialize configured public crawler captures into the canonical advisory read model.
2. Add the governed LLM extraction/review boundary without enabling unmanaged model calls.
3. Promote outcome journal/review to a first-class read model.
4. Add cloud-visible health/readiness checks for the completed product loop.

## Product Objective

Make the AI Infrastructure Trading Advisory Workstation progress from a fixture-backed cockpit to a continuously refreshable advisory analyst loop.

This improves:

- source monitoring
- evidence quality
- catalyst detection
- segment impact mapping
- equity thesis quality
- risk regime awareness
- advisory brief usefulness
- journal/outcome review quality

## Governing Specs

- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0008-model-routing-and-audit.md`
- `docs/specs/0009-evaluation-harness.md`
- `docs/specs/0013-llm-routing-and-governance.md`
- `docs/specs/0015-containerized-deployment.md`
- `docs/specs/0016-equity-intelligence-crawler.md`
- `docs/specs/0017-crawl-pipeline-runtime.md`

## Allowed Files

- `packages/core/**`
- `services/api/**`
- `services/worker/**`
- `scripts/**`
- `deploy/**`
- `tests/**`
- `docs/CURRENT_TASK.md`
- `docs/plans/active/current-plan.md`
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
- no unmanaged model calls
- no model names hard-coded in business logic
- no scoring, risk, constraints, target weights, or PnL owned by LLM output
- no DuckDB/Parquet v1 dependency

## Input Contract

Configured public crawler sources, crawl captures, existing fixture-backed advisory objects, manual local trade journal entries, and governed model-router configuration.

## Output Contract

The remaining sessions must preserve and extend this advisory-only loop:

```text
SourceFrontier
-> SourceSignal
-> EvidenceItem
-> MarketEvent
-> SegmentImpact
-> EquityImpactAssessment
-> ValuationContext / RiskRegime
-> TradingAdvisory
-> AnalystBrief
-> OutcomeJournal
```

Every persisted object must expose provenance, freshness, and advisory-only state where applicable.

## Acceptance Criteria

- crawler success path writes canonical `analyst.source_signals` and `analyst.market_events` rows, not only legacy `signals.equity_events`
- crawler-derived read-model records include source URL, source kind, evidence IDs, content hash, timestamps, confidence, and review status
- LLM extraction/review boundary can only emit governed drafts and ModelRun audit metadata; it cannot emit scores, weights, constraints, orders, executions, or trade instructions
- outcome journal/review objects link manual journal entries to advisory, MarketEvent, evidence, invalidation, risk flags, and PnL attribution fields
- read-only APIs expose latest outcome-review state and freshness metadata
- cloud/readiness checks can detect latest crawler source signal, latest MarketEvent, latest analyst brief, latest outcome review, and API readiness
- all new routes are read-only unless they are existing local manual journal endpoints
- architecture policy tests pass

## Tests To Add Or Run

- targeted tests for crawler canonical materialization
- targeted tests for governed LLM extraction boundary
- targeted tests for outcome journal/read-model repository and API
- targeted tests for cloud/readiness checks
- `./.venv/bin/python -m unittest tests.test_architecture_policy`
- `./.venv/bin/python -m unittest discover -s tests`
- `python3 -m compileall packages services tests`
- `npm run build --prefix apps/web` if frontend files change
- `npm audit --omit=dev --prefix apps/web` if frontend/dependency files change
- `docker compose config`
- `scripts/compose_smoke.sh`
- `git diff --check`

## Definition Of Done

- implementation complete for scoped remaining sessions
- relevant RED/GREEN tests added
- architecture policy tests pass
- full Python suite passes
- build/compile checks pass
- cloud deployment validation completed for runtime/deploy changes
- `docs/BUILD_LOG.md` updated
- changes committed and pushed
- remaining gaps documented
