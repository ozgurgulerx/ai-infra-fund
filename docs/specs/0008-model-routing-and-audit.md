# 0008 Model Routing And Audit

## Purpose

Define model routing, fallback chains, and audit requirements.

## Source Of Truth

Model identities, deployments, task roles, cost class, context limits, allowed data classes, and fallback chains must live in `config/model_profiles.yaml`.

Business logic must not hard-code model names.

## Required Task Roles

- `source_classification`
- `evidence_summary`
- `orchestration_validation`
- `adversarial_review`
- `local_fallback`
- `embeddings`

## Audit

Every model call must create a `ModelRun` record. Failures and denied calls must also be auditable.

## Data Policy

The router must check data class before cloud calls. Private research is local-only by default.
