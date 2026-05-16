# Updated Plan: Auditable Model-Routed Trading System

## Assessment

The suggestions are mostly correct and should tighten the architecture. The key rule becomes:

LLMs interpret evidence and explain recommendations; deterministic code computes signals, risk, backtests, constraints, and target weights.

This avoids an opaque "LLM portfolio manager" and keeps recommendations reproducible, testable, and auditable.

The system is local-first, advisory-only, and cloud-model-assisted via Azure AI Foundry. Cloud models may classify, extract, summarize, review, and explain, but deterministic code owns scoring, risk, backtests, constraints, and target weights.

## Azure AI Foundry Context

Use this deployment context for cloud-model-assisted workflows:

- Account/user context: `ozgurguler@microsoft.com`
- Subscription name: `MCAPS-Hybrid-REQ-102171-2024-ozgurguler`
- Resource group: `rg-ozgurguler-7212`
- AI Services resource: `ozgurguler-7212-resource`
- Project: `ozgurguler-7212`
- Region: `northcentralus`
- Foundry API endpoint: `https://ozgurguler-7212-resource.services.ai.azure.com/api/projects/ozgurguler-7212`

Deployed models:

- `gpt-5-nano`
- `gpt-5-mini`
- `text-embedding-3-small`
- `DeepSeek-V3.2`
- `Kimi-K2-Thinking`
- `Kimi-K2.6`
- `DeepSeek-V4-Flash`

Do not store credentials in the repo. Store deployment names and routing policy in `config/model_profiles.yaml`; read secrets from the local environment or a secret manager.

## Model Routing

Use a configurable model router, not one model everywhere:

| Role | Default |
|---|---|
| Source classification, dedupe, light metadata | gpt-5-nano |
| Evidence summaries and draft recommendation narratives | DeepSeek-V4-Flash |
| Structured orchestration, schema repair, validation retries | gpt-5-mini |
| Adversarial thesis review and contradiction checks | Kimi-K2.6 |
| Local fallback | qwen3:30b, deepseek-r1:32b |
| Embeddings | local bge-m3 first |

Do not hard-code these names in business logic. Store them in `config/model_profiles.yaml` with deployment, quota notes, cost class, max context, allowed tasks, privacy policy, and fallback chain.

## `config/model_profiles.yaml` Schema

Each model profile must include:

- `model_id`
- `deployment`
- `provider`
- `endpoint_type`
- `task_roles`
- `quota_rpm`
- `quota_tpm`
- `cost_class`
- `max_context`
- `privacy_class`
- `allowed_data_classes`
- `fallback_chain`
- `structured_output_support`
- `notes`

Business logic consumes task roles and fallback chains from this file. It must not branch on literal model names.

## Pipeline Changes

- Ingest
  - Parse PDFs, filings, CSVs, market data, and futures data deterministically where possible.
  - Use gpt-5-nano for ticker/theme/source classification.
  - Use DeepSeek-V4-Flash for evidence summaries.
  - Use Kimi-K2.6 only for long/conflicted reports or weekly thesis review.
- Evidence Normalization
  - Add EvidenceItem, EvidenceClaim, and source provenance.
  - Every claim must link to source URI, content hash, timestamp, ticker/theme, horizon, confidence, and span reference.
- Signal Computation
  - LLMs extract claims/features only.
  - Python computes strategic thesis score, forward indicator score, tactical technical score, and portfolio risk score.
  - Score formulas are versioned in config.
- Portfolio Recommendation
  - Deterministic module generates TargetWeights.
  - LLM explains the result and cites evidence.
  - Enforce max single-name weight, max theme exposure, cash floor, liquidity floor, turnover cap, drawdown response, and thesis staleness penalty.
- Review Pass
  - DeepSeek-V4-Flash drafts the explanation.
  - Kimi-K2.6 performs adversarial review.
  - gpt-5-mini validates schema and emits final structured artifact.

## New Contracts

- EvidenceItem
  - evidence_id, source_uri, content_hash, timestamp, license_label, tickers, themes, summary
- EvidenceClaim
  - claim_id, evidence_id, ticker_or_theme, claim_type, direction, magnitude, time_horizon, confidence, quote_or_span_ref
- ModelRun
  - model, deployment, prompt_version, input_hash, output_hash, latency_ms, token_estimate, schema_valid, retry_count
- SignalBundle
  - signal_bundle_id, ticker, strategic_thesis_score, forward_indicator_score, tactical_technical_score, portfolio_risk_score, formula_versions
- TargetWeights
  - target_weights_id, weights, cash_weight, constraints, source_signal_ids, generated_by
- RecommendationArtifact
  - recommendation_id, ticker_or_portfolio, advisory_label, action, horizon, score_breakdown, target_weights_id, evidence_ids, model_run_ids, risks
- RecommendationAudit
  - recommendation_id, target_weights_id, evidence_ids, signal_bundle_id, model_runs, deterministic_checks, reviewer_findings
- RunArtifact
  - run_id, run_type, started_at, completed_at, inputs_hash, output_hash, artifact_uri, status

Every recommendation artifact must include evidence IDs, model run IDs, signal bundle ID, target weights ID, and advisory-only labeling.

## Storage

- PostgreSQL + pgvector: canonical facts, portfolio records, trade journal, evidence metadata, evidence claims, embeddings, run ledger, model runs, market snapshots, factor rows, signal bundles, target weights, recommendation artifacts, audits, backtest summaries, evaluation results, and local semantic retrieval.
- Ignored local filesystem: raw PDFs, CSVs, downloaded reports, and exports, with metadata and hashes in PostgreSQL.
- DuckDB + Parquet: future optional analytical scale-out only, not a v1 dependency.
- Azure Search remains optional. V1 is local-first and Azure Foundry model-assisted, not dependent on Azure Search.

Storage and data-class policy details live in:

- `docs/plans/data_plan.md`
- `docs/plans/llm_plan.md`

## Spec Updates

Add or update:

- `docs/specs/0004-agent-contracts.md`: model routing, structured outputs, validation rules.
- `docs/specs/0008-model-routing-and-audit.md`: model profiles, fallback chains, ModelRun ledger.
- `docs/specs/0009-evaluation-harness.md`: model benchmark set and scoring rubric.
- `docs/specs/0010-repo-patterns-architecture.md`: repo layout and dependency boundaries.
- `docs/specs/0011-implementation-roadmap.md`: phase order and gates.
- `docs/specs/0012-data-architecture.md`: storage ownership and data-class policy.
- `docs/specs/0013-llm-routing-and-governance.md`: Azure Foundry routing, fallback chains, and ModelRun governance.
- `docs/specs/0014-risk-monitoring-and-incidents.md`: model-routing incident handling and recommendation suppression.
- `AGENTS.md`: LLMs may extract, summarize, classify, review, and explain, but deterministic modules own scores, risk, backtests, and target weights.

## Hard Rules

- No live order placement or broker execution endpoint.
- LLMs may extract, summarize, classify, review, and explain.
- Deterministic code owns scores, risk, backtests, constraints, and target weights.
- Business logic must not hard-code model names.
- Every recommendation must include evidence IDs, model run IDs, and advisory-only labeling.
- TargetWeights must be generated by portfolio code, not directly by an LLM.
- Any deviation from specs must be called out explicitly before implementation continues.

## Implementation Controls

Use these controls when implementing model routing:

- `AGENTS.md` defines non-negotiable rules.
- `config/model_profiles.yaml` is the only source for model identities, deployments, task roles, and fallback chains.
- Architecture policy tests enforce no hard-coded model names outside config and tests.
- `everything-claude-code:tdd-workflow` applies to router, contracts, and validation code.
- `everything-claude-code:eval-harness` applies to model benchmark and shadow-mode scoring.
- `everything-claude-code:security-review` applies to Azure Foundry endpoint, credentials, privacy class, and allowed data classes.
- Future `fund-model-routing-review` skill should check model profiles, fallback chains, `ModelRun` ledger, and structured-output validation.

After model-routing implementation, use parallel subagents:

- spec-trace reviewer
- architecture-policy reviewer
- test-gap reviewer
- security/provenance reviewer
- financial-safety reviewer

Fix HIGH/CRITICAL findings before closing the phase.

## Model Evaluation Harness

Before locking routing, build a benchmark set:

- 10 SemiAnalysis-style reports.
- 10 earnings/news events.
- 10 portfolio recommendation cases.
- 10 backtest/report-generation cases.

Score models on:

- schema pass rate,
- citation accuracy,
- numeric correctness,
- contradiction detection,
- latency,
- cost,
- final recommendation usefulness.

Run DeepSeek-V4-Flash, Kimi-K2.6, and gpt-5-mini in shadow mode for one week before finalizing routing defaults.

## Assumptions

- The listed model deployments and quotas are user-provided and treated as current defaults.
- Kimi is a reviewer, not the workhorse.
- Local embeddings are preferred for privacy and cost. `text-embedding-3-small` may be used through Azure AI Foundry only for allowed data classes.
- No model is allowed to create final numeric scores or target weights directly.
