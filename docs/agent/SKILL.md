---
title: ai-infra-fund agent bootstrap
status: advisory-only
audience: external AI agents (Claude Code, Codex, Cursor, etc.)
---

# ai-infra-fund Agent Bootstrap

This document is the single entry point for any AI agent that wants to
consume the ai-infra-fund advisory surface. Read it once, then call the
read endpoints listed below.

## What this system is

`ai-infra-fund` is a local-first, **advisory-only** equity research and
portfolio recommendation system for AI infrastructure, the broader AI
ecosystem, and quantum technology investing. The system ingests evidence,
classifies and summarizes it under governed model routes, computes
deterministic signals, generates deterministic target weights, and exposes
auditable portfolio recommendations.

## Non-negotiable safety boundary

- **advisory-only**: every artifact carries the advisory label.
- No live order placement. No broker connection. No order routing. No
  execution surface.
- Deterministic code owns scores, risk, backtests, constraints, and target
  weights. LLMs may extract, summarize, classify, review, and explain.
- PostgreSQL + pgvector is the v1 durable store.

## Forbidden agent actions

Agents must not:

- Attempt placing, submitting, routing, or executing real-world trades
  using this surface or any companion system.
- Stage any UI action that implies a real market order.
- Treat target weights as instructions to a broker. They are advisory
  artifacts that a human reviews and acts on manually.

## Base URL

- Local development: `http://localhost:8000`
- Inside Docker Compose (service-to-service): `http://api:8000`
- AKS: per the ingress configured in `deploy/aks-ai-infra-fund.yaml`

## Authentication

None. The advisory API is internal/local. Network reachability is the
access boundary; treat published endpoints as read-only by contract.

## Response envelope

Successful reads return:

```json
{ "data": { "...": "..." } }
```

Errors return:

```json
{ "error": { "code": "<machine_code>", "message": "<human readable>" } }
```

## ID prefix glossary

| Prefix              | Object                       |
| ------------------- | ---------------------------- |
| `evidence-`         | EvidenceItem                 |
| `evidence-chunk-`   | EvidenceChunk                |
| `claim-`            | EvidenceClaim                |
| `model-run-`        | ModelRun                     |
| `signal-bundle-`    | SignalBundle                 |
| `target-weights-`   | TargetWeights                |
| `recommendation-`   | RecommendationArtifact       |
| `audit-`            | RecommendationAudit          |
| `evaluation-`       | EvaluationRun                |
| `strategy-`         | Strategy                     |
| `dataset-snapshot-` | DatasetSnapshot              |
| `run-`              | RunArtifact                  |
| `audit-evt-`        | ExperimentEvent (event log)  |
| `backtest-req-`     | BacktestRequest (queued job) |

## Endpoint catalog (read paths)

### Liveness & version

- `GET /health` — service liveness.
- `GET /version` — project / service / version label.
- `GET /ready` — readiness incl. database probe.

### Agent bootstrap

- `GET /internal/agent/skill` — this document.
- `GET /internal/agent/openapi.json` — live OpenAPI 3.1 spec.
- `GET /internal/agent/openapi.yaml` — committed YAML snapshot.

### Advisory artifacts

- `GET /internal/recommendations/{recommendation_id}` — fetch a
  recommendation with its audit links.
- `GET /internal/runs/latest` — most recent run artifact.
- `GET /internal/runs/{run_id}` — run by ID.
- `GET /internal/advisory-chain/latest` — most recent advisory chain
  trace.
- `GET /internal/advisory-chain/demo` — seeded demo chain.

### Dashboard summaries

- `GET /internal/dashboard/recommendation-summary`
- `GET /internal/dashboard/evaluation-summary`
- `GET /internal/dashboard/evidence-summary`
- `GET /internal/dashboard/model-run-summary`
- `GET /internal/dashboard/data-quality-summary`
- `GET /internal/dashboard/incident-summary`
- `GET /internal/dashboard/watchlist-summary`
- `GET /internal/dashboard/crawl-frontier-health`
- `GET /internal/dashboard/latest-equity-events`
- `GET /internal/dashboard/latest-signal-snapshots`
- `GET /internal/dashboard/latest-advisory-run`
- `GET /internal/dashboard/ticker-intelligence/{ticker}` (uppercase ticker)
- `GET /internal/status/overview`
- `GET /internal/status/modules`

### Local trade journal

- `GET /internal/trade-journal/entries?limit=25` — manual journal entries.
  Journal-only; flagged `advisory_only`.

### Evidence ingestion (advisory, no execution)

- `POST /internal/evidence/manual` — accept hand-curated evidence.
- `POST /internal/evidence/file` — accept a local evidence file index.

### Evaluation persistence

- `POST /internal/evaluations` — persist a backtest run artifact.

## Recommended agent flow

1. `GET /internal/agent/skill` — read this document.
2. `GET /internal/agent/openapi.json` — discover the full schema set.
3. `GET /internal/advisory-chain/latest` — see the freshest advisory
   chain trace.
4. `GET /internal/dashboard/recommendation-summary` — current
   recommendation set.
5. For each recommendation of interest, follow the linked IDs:
   - `recommendation-...` -> `/internal/recommendations/{id}`
   - `run-...` -> `/internal/runs/{id}`
6. Surface findings to a human. Do **not** take execution action.

## Reading the recommendation envelope

A recommendation artifact references its full provenance:

- `evidence_ids` — the supporting evidence items.
- `model_run_ids` — every model run that contributed.
- `signal_bundle_id` — the deterministic signal bundle.
- `target_weights_id` — the deterministic target weights.
- `audit_id` — the recommendation audit record.
- `advisory_label` — always `advisory_only`.

If any link is missing, the recommendation should be treated as
incomplete and not surfaced to a human.

## Versioning

- API version is reported by `GET /version`.
- The committed OpenAPI snapshot at `docs/api/openapi.yaml` is the
  contractual reference. Re-generate it via
  `python scripts/export_openapi.py`. CI fails if the committed YAML
  drifts from the live FastAPI spec.

## Where to find more

- Product vision: `docs/specs/0001-product-vision.md`
- Trading policy (advisory boundary): `docs/specs/0002-trading-policy.md`
- Data contracts: `docs/specs/0003-data-contracts.md`
- Agent contracts: `docs/specs/0004-agent-contracts.md`
- Repository overview: `README.md`
