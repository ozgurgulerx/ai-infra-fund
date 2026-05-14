# 0013 LLM Routing And Governance

## Purpose

Define how cloud and local models are used safely.

## Routing

All routing is driven by `config/model_profiles.yaml`.

Default roles:

- lightweight source classification
- evidence summaries
- orchestration validation
- adversarial thesis review
- local fallback
- embeddings

## Governance

- no credentials in repo
- no hard-coded model names in business logic
- private research local-only by default
- data-class checks before cloud calls
- every model call creates a ModelRun record
- deterministic code continues when LLM calls fail
