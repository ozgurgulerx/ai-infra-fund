# V1 Release Checklist

## Purpose

This document freezes the `v1.0` release scope for the AI Infrastructure Trading Advisory Workstation.

`v1.0` is an advisory/reporting release. It proves that configured public-source monitoring, evidence materialization, DB-backed advisory generation, governed shadow analyst audit, deterministic quality gates, and API-backed workstation surfaces work under the no-execution boundary.

## Current Readiness Statement

The `v1.0` product scope is frozen and documented.

The repo should not be tagged until release hygiene and final validation are complete:

- worktree is clean;
- release docs are committed;
- deployment manifests match the release deployment or intentional drift is documented;
- final local and cloud validation are rerun from the exact release commit.

## Scope Rule

`v1.0` does not require every real model call to succeed. It requires every model success, failure, timeout, denial, and fallback to be audited through `ModelRun` records, to be fallback-safe, and to never publish raw LLM draft text directly.

## 1. Product Boundary

Required for `v1.0`:

- [ ] Product remains advisory and reporting only.
- [ ] No broker integration exists.
- [ ] No live order placement exists.
- [ ] No execution endpoint exists.
- [ ] No execution-like UI control exists.
- [ ] Manual buy/sell records are local journal entries only.
- [ ] Advisory labels are limited to analyst guidance such as `watch`, `accumulate`, `hold`, `trim`, `avoid`, and `exit-candidate`.
- [ ] LLM outputs are draft/review artifacts until deterministic gates validate them.
- [ ] Deterministic code owns numeric scores, constraints, target weights, entry/exit levels, PnL, readiness checks, and publication gates.

## 2. Data Pipeline

Required for `v1.0`:

- [ ] `config/source_registry.yaml` seeds configured public sources.
- [ ] Source registry seeding is idempotent.
- [ ] Missing optional provider secrets do not block public source seeding.
- [ ] Crawler leases configured frontier rows.
- [ ] Crawler writes crawl logs for success and failure paths.
- [ ] Successful public captures create `EvidenceItem` records.
- [ ] `EvidenceItem` records create `SourceSignal` records.
- [ ] `SourceSignal` and evidence records create typed `MarketEvent` records.
- [ ] MarketEvents link to evidence IDs and provenance metadata.
- [ ] Stale, missing, private, low-quality, or unsupported source material is suppressed or quarantined with explicit reasons.
- [ ] Daily brief worker consumes DB-backed `EvidenceItem`, `SourceSignal`, and `MarketEvent` rows, not fixture-only data.
- [ ] Daily brief worker produces `AnalystBrief`, `TradingAdvisory`, and `audit.run_artifacts`.

## 3. LLM Intelligence

Required for `v1.0`:

- [ ] Real model call path exists behind `config/model_profiles.yaml`.
- [ ] Business logic does not hard-code model deployment names.
- [ ] Every model call attempt creates an `audit.model_runs` record.
- [ ] Public/allowed analyst context can route to a configured cloud model when provider auth is available.
- [ ] Provider success, failure, timeout, denial, and fallback are all auditable.
- [ ] `private_research` cloud routing is denied by default.
- [ ] Shadow analyst context includes evidence, source signals, market events, segment impacts, equity assessments, valuation context, risk regime, portfolio exposure, prior advisories, and outcome journal context where available.
- [ ] Shadow analyst drafts include evidence IDs, context used, decision rationale, material claims, and ticker-specific implications where evidence supports them.
- [ ] Raw capture IDs are provenance context only and cannot substitute for canonical evidence IDs in material claims.
- [ ] LLM output does not own final scores, target weights, PnL, accounting, or readiness gates.
- [ ] Fallback mode remains available and keeps daily brief generation successful when real model calls fail.

Not required for `v1.0`:

- Every latest real model call succeeding.
- Automatic LLM draft promotion.

## 4. Quality Gate

Required for `v1.0`:

- [ ] Deterministic quality evaluator exists for shadow analyst drafts.
- [ ] Quality evaluator checks evidence coverage, evidence ID validity, claim-to-evidence support, forbidden execution language, advisory-only language, specificity, ticker/segment coverage, uncertainty quality, context completeness, rationale usefulness, hallucinated ticker/source references, and stale evidence usage.
- [ ] Unknown material evidence IDs are blocking.
- [ ] Unknown `context_used` IDs are blocking only when absent from the supplied analyst context bundle.
- [ ] Valid known capture IDs in `context_used` do not block review.
- [ ] Drafts are classified as `reject`, `keep_review_required`, or `eligible_for_human_review`.
- [ ] Raw draft text is not published into `AnalystBrief` or `TradingAdvisory`.
- [ ] Manual review foundation exists and rejects unsafe promotion attempts.
- [ ] Published advisory payloads include advisory label, evidence IDs, model run IDs where applicable, readiness checks, deterministic checks, and audit linkage.

Deferred to `v1.1`:

- Automatic draft promotion.
- Full human-review workflow polish.

## 5. UI And API

Required for `v1.0`:

- [ ] Daily cockpit renders the latest DB-backed analyst brief.
- [ ] Daily cockpit renders latest advisory labels and risk/invalidation context.
- [ ] Daily cockpit shows evidence references and audit links where available.
- [ ] Ticker workbench renders live theme intelligence.
- [ ] Ticker workbench normalizes source display text and does not show raw provider JSON as analyst-facing copy.
- [ ] Segment map endpoint works.
- [ ] Portfolio exposure endpoint works.
- [ ] Outcome journal endpoint exists.
- [ ] Manual journal/outcome path exists as local journal/reporting only.
- [ ] UI contains no business logic for scores, weights, constraints, PnL, or model routing.
- [ ] UI contains no broker connection, order placement, order routing, execution, fill, or automated trading control.

Deferred to `v1.1` unless already deployed:

- LLM review-status UI.
- Quality-gate status panel in the cockpit/ticker/ops UI.
- Richer portfolio analytics.
- Additional UI polish.

## 6. Cloud Runtime

Required for `v1.0`:

- [ ] Cloud API `/health` passes.
- [ ] Cloud API `/ready` passes.
- [ ] Cloud worker deployment is healthy.
- [ ] Cloud migrations are applied successfully.
- [ ] Cloud database contains source registry, crawl, evidence, source signal, MarketEvent, advisory, model run, and shadow draft tables required by v1.0.
- [ ] Cloud run validates source registry seed.
- [ ] Cloud run validates crawl materialization.
- [ ] Cloud run validates daily AI infrastructure brief generation.
- [ ] Cloud run validates one real model-routed shadow analyst success or an auditable provider failure/denial/timeout with deterministic fallback.
- [ ] Cloud cockpit renders against the deployed backend.
- [ ] Release evidence includes image tags, commit hash, run artifact ID, latest brief ID, latest model run ID, latest draft ID, and health/readiness output.

Deferred to `v1.1`:

- Automated scheduled production runs.
- Making the latest real LLM call always succeed.
- Broader source-provider hardening.

## 7. Guardrails

Required for `v1.0`:

- [ ] Full Python test suite passes.
- [ ] Architecture policy tests pass.
- [ ] Frontend build passes when frontend files changed.
- [ ] `npm audit --omit=dev --prefix apps/web` passes when frontend dependencies are relevant.
- [ ] `python3 -m compileall packages services tests` passes.
- [ ] `git diff --check` passes.
- [ ] No secrets, `.env`, private reports, raw private research, or provider keys are tracked.
- [ ] PostgreSQL + pgvector remains the v1 canonical data spine.
- [ ] DuckDB/Parquet remains future optional only.
- [ ] No raw LLM draft publication path exists.
- [ ] No broker/order/execution behavior exists in code, API, worker, UI, docs, or config outside explicit forbidden-boundary documentation.

## 8. Known V1.1 Follow-Ups

- Automatic draft promotion.
- LLM review-status UI if not already deployed.
- Quality-gate status panel if not already deployed.
- Scheduled production automation.
- External valuation-data integrations.
- Full portfolio analytics.
- External analyst consensus.
- Broader source-provider hardening.
- Making the latest real LLM call always succeed.
- More UI polish.
- Expanded source freshness monitoring and alerting.
- Deeper analyst-brief scoring calibration against outcome journal history.

## V1.0 Completion Rule

Declare `v1.0` complete only after:

1. Required `v1.0` checklist items are checked or explicitly documented as satisfied by release evidence.
2. The release commit is deployed to cloud.
3. Cloud `/health` and `/ready` pass.
4. The latest cloud daily brief run produces DB-backed `AnalystBrief` and `TradingAdvisory` records.
5. A real or auditable-fallback shadow analyst run creates `ModelRun` and shadow draft records.
6. The cockpit and ticker workbench render deployed data.
7. `docs/BUILD_LOG.md` records the release verification evidence.
8. Any deferred item is listed under the `v1.1` follow-up section rather than treated as a hidden blocker.

## Latest Audited Validation Snapshot

This snapshot records the latest known validation evidence. The final release owner must rerun the commands from the exact release commit before tagging.

Local validation:

| Command | Latest audited result |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests` | passed, 744 tests, 3 skipped |
| `./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_openapi_export_sync` | passed, 44 tests |
| `python3 -m compileall packages services tests` | passed |
| `npm run build --prefix apps/web` | passed |
| `npm audit --omit=dev --prefix apps/web` | passed, 0 vulnerabilities |
| `docker compose config` | passed |
| `scripts/compose_smoke.sh` | passed |
| `git diff --check` | passed |

Cloud validation:

| Check | Latest audited result |
|---|---|
| API deployment | `1/1` ready on `aistartuptr.azurecr.io/ai-infra-fund-api:faa5b6d-runtime` |
| Worker deployment | `1/1` ready on `aistartuptr.azurecr.io/ai-infra-fund-worker:faa5b6d` |
| Web App Service | running on `aistartuptr.azurecr.io/ai-infra-fund-web:7c21cf9` |
| `/api/backend/health` | passed |
| `/api/backend/ready` | passed |
| `/api/backend/internal/analyst-brief/latest` | passed, latest brief `brief-daily-ai-infra-20260518T055305Z-268cb5ec` |
| `/api/backend/internal/trading-advisory/latest` | passed |
| `/api/backend/internal/ticker/NVDA/workbench` | passed |
| `/api/backend/internal/ticker/CEG/workbench` | passed |
| `/api/backend/internal/segment-map/latest` | passed |
| `/api/backend/internal/portfolio/exposure/latest` | passed |

Cloud database snapshot:

| Object | Count |
|---|---:|
| `evidence.source_frontier_urls` | 417 |
| `evidence.crawl_logs` | 816 |
| `evidence.source_raw_captures` | 196 |
| `evidence.evidence_items` | 67 |
| `analyst.source_signals` | 223 |
| `analyst.market_events` | 223 |
| `analyst.analyst_briefs` | 17 |
| `analyst.trading_advisories` | 69 |
