# Spec Router

Codex must not read every spec for every task.

Always read:

- AGENTS.md
- docs/PRODUCT.md
- docs/ARCHITECTURE.md
- docs/CURRENT_TASK.md

Then read only the specs listed below for the task type.

## Product or Policy Changes

- specs/0001-product-vision.md
- specs/0002-trading-policy.md

## Contract / Schema Changes

- specs/0003-data-contracts.md
- specs/0012-data-architecture.md

## LLM / Agent / Model Router Changes

- specs/0004-agent-contracts.md
- specs/0008-model-routing-and-audit.md
- specs/0013-llm-routing-and-governance.md

## Evidence / Thesis / Research Changes

- specs/0007-situational-awareness-thesis-map.md
- specs/0016-equity-intelligence-crawler.md
- specs/0017-crawl-pipeline-runtime.md

## Signal / Alpha / Forward Indicator Changes

- specs/0006-forward-indicators.md
- docs/ALPHA_ANALYST_PRINCIPLES.md
- specs/0009-evaluation-harness.md

## Data / Storage / Migration Changes

- specs/0012-data-architecture.md
- specs/0015-containerized-deployment.md

## Risk / Incident Changes

- specs/0014-risk-monitoring-and-incidents.md
- specs/0002-trading-policy.md

## UI Changes

- specs/0005-ui-acceptance.md
- specs/0002-trading-policy.md

## Deployment Changes

- specs/0015-containerized-deployment.md
- docs/HARNESS.md

## Roadmap / Phase Changes

- specs/0011-implementation-roadmap.md
- docs/HARNESS.md

## Rule

If CURRENT_TASK.md references a spec, Codex must read it.

If a spec is not referenced, Codex should not load it unless the task clearly requires it.
