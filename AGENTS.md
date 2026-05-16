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
- Every analyst evaluation and decision point must be LLM-mediated, evidence-linked, and auditable. LLMs classify, extract, summarize, review, critique, and explain catalysts, contradictions, risk framing, readiness, and recommendation rationale through configured routes only.
- Deterministic code still owns numeric scores, risk math, backtests, constraints, target weights, scenario values, entry/exit levels, PnL, hard readiness checks, and publication/suppression gates. LLM review cannot bypass failed deterministic checks.
- Model routing must use `config/model_profiles.yaml`; business logic must not hard-code model names.
- PostgreSQL + pgvector is the v1 canonical data spine. DuckDB/Parquet is future optional only.
- Every model call creates a `ModelRun` record.
- Every recommendation includes advisory label, evidence IDs, model run IDs, signal bundle ID, target weights ID, and deterministic checks.
- Private research is local-only by default. Cloud model calls must respect data-class policy.
- UI must not contain business logic or expose order placement.
- Never commit private reports, secrets, `.env`, or `.env.*`; use `.env.example` for placeholders only.
- Cloud deployment is the only deployment surface to reference in user-facing answers, status reports, URLs, and readiness claims. Do not refer to local deployment URLs, local Compose URLs, or localhost access unless the user explicitly asks for local development or debugging commands.
- The canonical frontend URL is `https://ai-infra-fund-frontend.azurewebsites.net`. Cloud health/readiness checks should use the frontend proxy paths under this host unless the task explicitly requires lower-level cloud infrastructure checks.

Hard forbidden:

- broker credentials
- live order placement
- order routing
- execution endpoints
- execution UI
- automated trading loops

## Working Loop

Use the phase-scoped harness in `docs/HARNESS.md`: fill `docs/CURRENT_TASK.md`, write or update tests first, confirm RED when product code changes, implement the smallest scoped change, run targeted tests plus architecture policy tests, then report verification and remaining gaps.

Treat this repo as the cloud-deployed codebase. After implementation and verification, deploy and validate the updated cloud stack unless the user explicitly asks for a dry run. Local Compose checks are development preflight only; they do not count as deployment validation and should not be presented as the deployment target.
