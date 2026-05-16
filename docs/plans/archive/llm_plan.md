# LLM Plan: Model Routing, Auditability, And Cost-Aware Performance

## Purpose

Define how large language models are used in the AI Infrastructure Fund Control Room.

The system is local-first and advisory-only, but cloud-model-assisted through Azure AI Foundry when the model router allows it. LLMs are used for evidence interpretation, classification, extraction, review, and explanation. Deterministic code owns scores, risk, backtests, constraints, and target weights.

The core LLM rule is:

LLMs may extract, summarize, classify, review, and explain. LLMs must not directly create final numeric scores, backtest results, portfolio constraints, or target weights.

## Architecture Boundary

LLMs are outside the deterministic decision core.

Allowed LLM responsibilities:

- classify sources, tickers, themes, and document types
- deduplicate similar evidence
- summarize evidence
- extract structured evidence claims
- identify contradictions and missing evidence
- draft human-readable recommendation explanations
- perform adversarial thesis review
- repair structured outputs when schema validation fails

Forbidden LLM responsibilities:

- computing final strategic thesis score
- computing final tactical technical score
- computing final forward indicator score
- computing final portfolio risk score
- generating final target portfolio weights
- deciding whether constraints pass
- creating backtest metrics
- changing formula versions
- placing or simulating live orders outside the evaluation harness

LLM outputs must become auditable artifacts before they influence recommendation explanations.

## Azure AI Foundry Context

Default cloud model access is through the existing Azure AI Foundry project.

Account context:

- Account: `ozgurguler@microsoft.com`
- Subscription: `MCAPS-Hybrid-REQ-102171-2024-ozgurguler`
- Resource group: `rg-ozgurguler-7212`
- AI Services resource: `ozgurguler-7212-resource`
- Project: `ozgurguler-7212`
- Region: `northcentralus`
- Foundry API endpoint: `https://ozgurguler-7212-resource.services.ai.azure.com/api/projects/ozgurguler-7212`

Detected deployed models:

| Deployment | Model | Provider / Format | Primary Use |
|---|---|---|---|
| `gpt-5-nano` | `gpt-5-nano` | OpenAI | cheap classification, routing, dedupe, metadata |
| `gpt-5-mini` | `gpt-5-mini` | OpenAI | orchestration, structured output, schema repair, validation retries |
| `text-embedding-3-small` | `text-embedding-3-small` | OpenAI | optional cloud embeddings for allowed data classes |
| `DeepSeek-V3.2` | `DeepSeek-V3.2` | DeepSeek | fallback analyst model |
| `Kimi-K2-Thinking` | `Kimi-K2.5` | MoonshotAI | fallback reviewer/thinking model |
| `Kimi-K2.6` | `Kimi-K2.6` | MoonshotAI | adversarial review, contradiction checks, complex synthesis |
| `DeepSeek-V4-Flash` | `DeepSeek-V4-Flash` | DeepSeek | primary cost-effective analyst model |

Observed quota notes should be captured in `config/model_profiles.yaml` and treated as operational defaults, not hard-coded business logic.

## Recommended Model Routing

Use a configurable model router. Do not hard-code model names in business logic.

| Task Role | Default Model | Fallback Chain | Notes |
|---|---|---|---|
| source_classification | `gpt-5-nano` | `gpt-5-mini`, local fallback | cheap ticker/theme/source labeling |
| dedupe_and_metadata | `gpt-5-nano` | `gpt-5-mini` | low-value, high-volume work |
| evidence_summary | `DeepSeek-V4-Flash` | `gpt-5-mini`, local fallback | default analyst summarization |
| evidence_claim_extraction | `DeepSeek-V4-Flash` | `gpt-5-mini`, `Kimi-K2.6` | requires schema validation |
| recommendation_narrative | `DeepSeek-V4-Flash` | `gpt-5-mini` | explanation only, not weights |
| adversarial_review | `Kimi-K2.6` | `Kimi-K2-Thinking`, `gpt-5-mini` | contradiction and missing-evidence review |
| schema_repair | `gpt-5-mini` | `gpt-5-nano` for simple cases | must preserve original semantics |
| final_artifact_validation | `gpt-5-mini` | deterministic validation only | validates structure, not investment truth |
| private_local_summary | `qwen3:30b` | `deepseek-r1:32b` | local-only data classes |
| local_reasoning_fallback | `deepseek-r1:32b` | `qwen3:30b` | offline second opinion |
| embeddings_local | `bge-m3` | none | default for local/private evidence |
| embeddings_cloud_allowed | `text-embedding-3-small` | `bge-m3` | only for allowed public data classes |

Primary performance recommendation:

- Use `DeepSeek-V4-Flash` as the default analyst model.
- Use `Kimi-K2.6` selectively as the high-quality reviewer.
- Use `gpt-5-mini` when structured outputs, schema repair, tool reliability, or orchestration matter.
- Use `gpt-5-nano` for cheap routing, classification, and metadata.
- Use local Ollama models for private/offline fallback, not as the performance path.

## Local Ollama Models

Local models are useful for privacy, offline work, and fallback. They are not expected to outperform the deployed Foundry models for this project.

Recommended local models:

| Model | Role |
|---|---|
| `bge-m3` | local embeddings for evidence chunks and claims |
| `qwen3:30b` | local general analyst fallback |
| `deepseek-r1:32b` | local reasoning fallback |

Optional local model:

| Model | Role | Caveat |
|---|---|---|
| `deepseek-r1:70b` | stronger local second-opinion reasoning | likely slower and memory-heavy on M3 Max 64 GB |

Do not plan to run `DeepSeek-V4-Flash`, `DeepSeek-V4-Pro`, or `Kimi-K2.6` locally. These are data-center-scale models and should be treated as cloud deployments.

## Model Profiles Configuration

All model routing must be driven by `config/model_profiles.yaml`.

Required fields:

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

Example shape:

```yaml
models:
  deepseek_v4_flash:
    model_id: DeepSeek-V4-Flash
    deployment: DeepSeek-V4-Flash
    provider: azure_foundry_deepseek
    endpoint_type: azure_ai_foundry
    task_roles:
      - evidence_summary
      - evidence_claim_extraction
      - recommendation_narrative
    quota_rpm: 500
    quota_tpm: 500000
    cost_class: low
    max_context: unknown
    privacy_class: cloud
    allowed_data_classes:
      - public_market_data
      - public_evidence
      - derived_analytics
    fallback_chain:
      - gpt_5_mini
      - local_qwen3_30b
    structured_output_support: true
    notes: Primary cost-effective analyst model.
```

The implementation must fail fast if a task role has no allowed model for the input data classes.

## Data-Class Routing Rules

The model router must inspect data classes before sending content to any model.

| Data Class | Cloud Model Default | Local Model Default |
|---|---|---|
| public_market_data | allowed | allowed |
| public_evidence | allowed | allowed |
| derived_analytics | allowed if no restricted source text | allowed |
| run_audit | metadata only unless allowed | allowed |
| user_portfolio | only if explicitly allowed by task policy | allowed |
| private_research | no by default | allowed |
| secrets | never | never |

For `private_research`, user-supplied paid reports, screenshots, and manual private notes should stay local by default. Cloud processing requires an explicit spec rule or user approval.

## Prompt And Schema Discipline

Every LLM task must have:

- task role
- prompt version
- input data classes
- expected JSON schema
- validation rules
- fallback chain
- retry policy
- audit logging

LLM output should be rejected if:

- schema validation fails after configured retries
- required evidence IDs are missing
- unsupported model produced the output
- data-class policy was violated
- output includes final target weights or final scores where not allowed
- content lacks provenance for claims

Schema repair must preserve the original model output semantics. It must not invent new evidence, scores, or claims.

## ModelRun Ledger

Every LLM call must create a `ModelRun` record.

Required fields:

- `model_run_id`
- `task_role`
- `model_id`
- `deployment`
- `provider`
- `prompt_version`
- `input_hash`
- `output_hash`
- `latency_ms`
- `token_estimate_input`
- `token_estimate_output`
- `cost_estimate`
- `schema_valid`
- `retry_count`
- `data_classes`
- `created_at`

Do not store secrets in the ledger. For private data, store hashes and metadata; only store raw input/output when allowed by data policy.

## Recommendation Flow

Recommendation generation should follow this sequence:

1. Load evidence and evidence claims.
2. Compute deterministic `SignalBundle`.
3. Generate deterministic `TargetWeights`.
4. Validate constraints deterministically.
5. Ask `DeepSeek-V4-Flash` to draft explanation using provided scores, weights, and evidence IDs.
6. Ask `Kimi-K2.6` for adversarial review when task importance warrants it.
7. Ask `gpt-5-mini` to validate or repair final structured artifact if needed.
8. Store all `ModelRun` records.
9. Store `RecommendationArtifact`.
10. Store `RecommendationAudit`.

No LLM can bypass deterministic scoring, deterministic target-weight generation, or deterministic constraint checks.

## Cost And Performance Policy

Performance is the primary requirement; cost is optimized through routing.

Default policy:

- Use cheap models for cheap tasks.
- Use `DeepSeek-V4-Flash` for most substantive analysis.
- Use `Kimi-K2.6` only where review quality matters.
- Use `gpt-5-mini` when schema reliability matters.
- Avoid repeated full-document calls; chunk and retrieve first.
- Cache summaries, claims, embeddings, and model outputs by content hash and prompt version.

Caching keys should include:

- content hash
- task role
- model profile version
- prompt version
- schema version

## Evaluation Harness

Before finalizing model routing defaults, run a benchmark set.

Benchmark corpus:

- 10 SemiAnalysis-style reports
- 10 earnings/news events
- 10 portfolio recommendation cases
- 10 backtest/report-generation cases

Score dimensions:

- schema pass rate
- citation accuracy
- numeric correctness
- contradiction detection
- latency
- cost
- final recommendation usefulness
- data-class policy compliance
- retry rate

Models to run in shadow mode:

- `DeepSeek-V4-Flash`
- `Kimi-K2.6`
- `gpt-5-mini`
- local `qwen3:30b`
- local `deepseek-r1:32b`

Run shadow evaluation for one week before changing production routing defaults.

## Testing Requirements

Unit tests:

- model profile schema validation
- task role to model resolution
- fallback chain resolution
- data-class allow/deny checks
- prompt version lookup
- output schema validation
- cache key stability

Integration tests:

- call model router with public evidence
- reject private research cloud route by default
- create `ModelRun` after model call
- retry and schema repair path
- recommendation artifact includes all model run IDs
- deterministic scoring works when LLMs fail

Architecture policy tests:

- no hard-coded model names outside `config/model_profiles.yaml` and tests
- signal modules do not import LLM clients
- portfolio modules do not import LLM clients
- target weight generator does not accept raw LLM output
- every recommendation contains advisory label, evidence IDs, and model run IDs
- no broker or order execution endpoint exists

Evaluation tests:

- model benchmark records latency and cost
- contradiction detection cases are scored
- citation accuracy cases are scored
- numeric correctness failures are caught
- shadow-mode outputs do not affect production recommendations until approved

## Security And Privacy

Model calls must respect the data plan.

Rules:

- Do not send secrets to any model.
- Do not send private paid reports to cloud models by default.
- Do not send full portfolio/cost-basis details to cloud models unless explicitly allowed.
- Prefer local embeddings for private evidence.
- Store raw prompts and outputs only when allowed.
- Store hashes for audit even when raw content is restricted.
- Redact account identifiers from cloud-bound prompts unless required and allowed.

## Operational Monitoring

Track model performance over time:

- latency by model and task role
- schema failure rate
- retry rate
- fallback rate
- estimated cost
- contradiction detection rate
- citation error rate
- data-class policy denials
- model outage incidents

If a model has sustained schema failures, high latency, or poor evaluation results, demote it in `model_profiles.yaml` rather than changing business logic.

## Phase Alignment

- Phase 0 creates `docs/specs/0013-llm-routing-and-governance.md`, `config/model_profiles.yaml`, and architecture policy tests.
- Phase 1 defines `ModelRun`, `EvidenceClaim`, `SignalBundle`, `TargetWeights`, `RecommendationArtifact`, `RecommendationAudit`, and `RunArtifact` contracts.
- Phase 3 implements model profile loading, task-role model resolution, fallback chains, data-class policy checks, prompt version registry, schema validation, retry policy, and `ModelRun` persistence.
- Phase 5 adds evidence extraction and summary routes.
- Phase 6 adds recommendation explanation, adversarial review, final schema validation, and audit persistence.
- Phase 7 adds model benchmark cases, shadow-mode model evaluation, and one-week routing review before defaults are finalized.

## Non-Goals For V1

- No LLM-created final scores.
- No LLM-created final target weights.
- No arbitrary LLM-generated code execution.
- No live trading or broker execution.
- No cloud processing of restricted data by default.
- No model-specific logic inside scoring, portfolio, or backtest modules.
