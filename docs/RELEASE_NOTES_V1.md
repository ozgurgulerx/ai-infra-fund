# Release Notes: v1.0

## Readiness Statement

`v1.0` is the first advisory/reporting release of the AI Infrastructure Trading Advisory Workstation.

The release is functionally scoped and documented. Final tagging still requires the release owner to confirm a clean worktree, commit this documentation, align or document deployment manifests, and rerun the final release validation from the release commit.

## 1. Product Scope

`v1.0` includes:

- advisory-only AI Infrastructure Trading Advisory Workstation;
- source registry driven public-source monitoring;
- configured public-source crawler materialization into `EvidenceItem`, `SourceSignal`, and `MarketEvent` records;
- DB-backed `AnalystBrief` and `TradingAdvisory` generation;
- API-backed Daily Trading Cockpit, ticker workbench, segment map, portfolio exposure, and outcome journal endpoints;
- governed shadow analyst pipeline;
- real model-call path through `config/model_profiles.yaml` with `ModelRun` audit;
- fallback-safe behavior when model calls fail, time out, or are denied;
- deterministic quality gate and manual review foundation for shadow analyst drafts;
- PostgreSQL + pgvector as the v1 durable data spine.

## 2. Advisory-Only Guardrails

`v1.0` explicitly excludes:

- broker integration;
- live order placement;
- order routing;
- execution endpoints;
- execution-like UI controls;
- automated trading loops;
- automatic LLM promotion;
- raw LLM draft publication;
- private research cloud routing by default;
- LLM-owned PnL, accounting, target weights, scenario math, readiness checks, or publication gates.

Manual buy/sell records are local journal/reporting records only. They do not submit, stage, route, transmit, or simulate live market orders.

## 3. Live Data Pipeline Status

The cloud deployment has demonstrated live public-source ingestion and materialization.

Latest audited cloud counts:

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

Latest audited cloud daily brief:

- run artifact: `run-daily-ai-infra-brief-268cb5ec85c9a575`
- analyst brief: `brief-daily-ai-infra-20260518T055305Z-268cb5ec`
- generated advisories: 22
- market events consumed: 25

## 4. LLM Shadow Analyst Status

The governed shadow analyst pipeline exists and is audited through `audit.model_runs` and `analyst.shadow_analyst_drafts`.

Current acceptance rule:

`v1.0` does not require every real model call to succeed. It requires every success, failure, timeout, denial, and fallback to create an auditable `ModelRun` and to keep daily brief generation fallback-safe.

Latest audited cloud model-run examples include:

- `model-run-91312213f1f433610499917e`: `azure_foundry`, `gpt-5-mini`, `analyst_brief_draft`, `success`, `schema_valid=true`.
- `model-run-dff8f45b820512afed288da3`: `azure_foundry`, `gpt-5-mini`, `analyst_brief_draft`, `failure`, `HTTP Error 403: Forbidden`, fallback-safe daily brief still succeeded.
- `model-run-429c6609d0bfde2c105ee5ff`: `azure_foundry`, `gpt-5-mini`, `analyst_brief_draft`, `failure`, timeout, fallback-safe behavior preserved.

Raw LLM drafts are not published directly into `AnalystBrief` or `TradingAdvisory`.

## 5. Quality Gate And Manual Review Status

`v1.0` includes:

- deterministic draft quality evaluator;
- checks for evidence coverage, evidence ID validity, claim-to-evidence support, forbidden execution language, advisory-only language, specificity, ticker/segment coverage, uncertainty quality, context completeness, rationale usefulness, hallucinated ticker/source references, and stale evidence usage;
- blocking behavior for unknown material evidence IDs;
- context ID semantics that separate material evidence IDs from source signals, MarketEvents, captures, and context objects;
- manual review foundation that prevents unsafe promotion.

`v1.0` does not include automatic draft promotion. Promotion workflow polish and LLM review-status UI are `v1.1` unless already deployed in the release candidate.

## 6. UI And API Surfaces

Validated API-backed surfaces:

- `/api/backend/health`
- `/api/backend/ready`
- `/api/backend/internal/analyst-brief/latest`
- `/api/backend/internal/trading-advisory/latest`
- `/api/backend/internal/ticker/NVDA/workbench`
- `/api/backend/internal/ticker/CEG/workbench`
- `/api/backend/internal/segment-map/latest`
- `/api/backend/internal/portfolio/exposure/latest`
- `/api/backend/internal/outcome-journal/latest`
- `/api/backend/internal/market-events/latest`
- `/api/backend/internal/source-signals/latest`

The hosted cockpit and ticker workbench render DB-backed advisory data, evidence references, risk/invalidation context, and advisory-only labels. The outcome journal endpoint exists; latest audited response was empty, which is acceptable for v1.0 as a foundation.

## 7. Cloud Deployment State

Observed cloud state during the v1.0 audit:

| Component | Image / State |
|---|---|
| API | `aistartuptr.azurecr.io/ai-infra-fund-api:faa5b6d-runtime` |
| Worker | `aistartuptr.azurecr.io/ai-infra-fund-worker:faa5b6d` |
| Web | `aistartuptr.azurecr.io/ai-infra-fund-web:7c21cf9` |
| AKS API deployment | `1/1` ready |
| AKS worker deployment | `1/1` ready |
| Frontend App Service | running |

Release closeout must either align checked-in deployment manifests to these tags or explicitly document intentional imperative deployment drift before tagging.

## 8. Validation Commands And Results

Latest audited local results:

| Command | Result |
|---|---|
| `./.venv/bin/python -m unittest discover -s tests` | passed, 744 tests, 3 skipped |
| `./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_openapi_export_sync` | passed, 44 tests |
| `python3 -m compileall packages services tests` | passed |
| `npm run build --prefix apps/web` | passed |
| `npm audit --omit=dev --prefix apps/web` | passed, 0 vulnerabilities |
| `docker compose config` | passed |
| `scripts/compose_smoke.sh` | passed |
| `git diff --check` | passed |

Required final validation before tag:

```bash
./.venv/bin/python -m unittest discover -s tests
./.venv/bin/python -m unittest tests.test_architecture_policy tests.test_openapi_export_sync
python3 -m compileall packages services tests
npm run build --prefix apps/web
npm audit --omit=dev --prefix apps/web
docker compose config
scripts/compose_smoke.sh
scripts/seed_public_sources.sh
scripts/crawl_materialization_smoke.sh
scripts/run_daily_ai_infra_brief_once.sh
git diff --check
```

Required final cloud validation before tag:

```bash
kubectl -n ai-infra-fund get deploy,pods,jobs -o wide
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/health
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/ready
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/analyst-brief/latest
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/trading-advisory/latest
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/ticker/NVDA/workbench
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/ticker/CEG/workbench
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/segment-map/latest
curl -sS https://ai-infra-fund-frontend.azurewebsites.net/api/backend/internal/portfolio/exposure/latest
```

## 9. Known V1.1 Gaps

- Automatic draft promotion.
- LLM review-status UI if not already deployed.
- Quality-gate status panel if not already deployed.
- Scheduled production automation.
- External valuation-data integrations.
- Full portfolio analytics.
- External analyst consensus.
- Broader source-provider hardening.
- Making the latest real LLM call always succeed.
- Expanded source freshness monitoring and alerting.
- Deeper analyst-brief scoring calibration against outcome journal history.
- Additional UI polish.
