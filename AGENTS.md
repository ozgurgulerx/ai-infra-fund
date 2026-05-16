# AI Infrastructure Fund Agent Instructions

## Default Read Set

Before changing code or docs, read only these files unless the task says otherwise:

1. `AGENTS.md`
2. `docs/PRODUCT.md`
3. `docs/ARCHITECTURE.md`
4. `docs/CURRENT_TASK.md`

Use `docs/SPEC_ROUTER.md` only to choose deeper canonical specs for the active task. Read deeper specs only when `docs/CURRENT_TASK.md` references them. Specs are canonical. Plans are temporary or archived. If a plan conflicts with a spec, the spec wins.

## Non-Negotiable Rules

- Product boundary: this repo builds an advisory and reporting-only AI Infrastructure Trading Advisory Workstation. It may generate trading advisory, thesis updates, valuation context, risk flags, trade plans, and journal reports. It must never automate trading or connect to brokers.
- Every implementation must improve at least one of: source monitoring, evidence quality, catalyst detection, segment impact mapping, equity thesis quality, valuation context, risk regime awareness, advisory brief usefulness, trade plan quality, or journal/outcome review quality.
- Advisory-only system: no live order placement, broker integration, execution endpoints, or execution-like UI controls.
- Manual buy/sell entry is local journal only and must not transmit orders.
- LLMs may classify, extract, summarize, review, and explain.
- Deterministic code owns scores, risk, backtests, constraints, and target weights.
- Model routing must use `config/model_profiles.yaml`; business logic must not hard-code model names.
- PostgreSQL + pgvector is the v1 canonical data spine. DuckDB/Parquet is future optional only.
- Every model call creates a `ModelRun` record.
- Every recommendation includes advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID, and deterministic checks.
- Private research is local-only by default. Cloud model calls must respect data-class policy.
- UI must not contain business logic or expose order placement.
- Never commit private reports, secrets, `.env`, or `.env.*`; use `.env.example` for placeholders only.

Hard forbidden:

- broker credentials
- live order placement
- order routing
- execution endpoints
- execution UI
- automated trading loops

## Working Loop

Use the phase-scoped harness in `docs/HARNESS.md`: fill `docs/CURRENT_TASK.md`, write or update tests first, confirm RED when product code changes, implement the smallest scoped change, run targeted tests plus architecture policy tests, then report verification and remaining gaps.

Treat this repo as the cloud-deployed codebase. After implementation and verification, deploy and validate the updated cloud stack unless the user explicitly asks for local-only work or a dry run. Local Compose checks are development preflight only; they do not count as deployment validation.
