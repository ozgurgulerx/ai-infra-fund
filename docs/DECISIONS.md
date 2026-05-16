# Decisions

## Accepted Decisions

- Advisory-only policy: the system produces research, recommendations, target-weight suggestions, audits, and local journal records; it never places or routes live orders.
- Manual trade entry is local journal only and must not transmit to brokers, venues, exchanges, or trading APIs.
- Deterministic/LLM boundary: LLMs classify, extract, summarize, review, and explain; deterministic code owns scores, risk, backtests, constraints, target weights, and publication checks.
- PostgreSQL + pgvector is the v1 canonical data spine for facts, evidence, embeddings, model runs, signals, recommendations, evaluations, and audit state.
- DuckDB/Parquet is future optional analytical scale-out only and is not a v1 dependency.
- Docker Compose service split is `web`, `api`, `worker`, `postgres`, and `migrate`; cloud deployments should preserve the same responsibilities.
- Model routing goes through `config/model_profiles.yaml`; business logic must not hard-code model names.
- Every model call creates a `ModelRun` record, including failures or denied calls where applicable.
- Every recommendation includes advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID, and deterministic checks.
- The crawler is advisory evidence ingestion and typed event materialization, not trading execution.
- Private research is local-only by default; cloud model calls must respect data-class policy.
- Private reports, credentials, `.env`, and `.env.*` must not be committed or copied into prompts, logs, tickets, docs, or generated artifacts.
- UI renders API data only; it must not contain business logic, direct database access, or order-placement controls.

## Open Decisions

- Exact future analytical scale-out trigger for DuckDB/Parquet remains undefined.
- Production-grade secret manager, backup/restore, monitoring, and incident runbooks remain deployment-specific.
- Future private-research cloud-processing exceptions require explicit user approval and spec updates.
