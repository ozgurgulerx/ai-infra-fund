# Active Plan

## Current Status

The fixture-backed advisory read model, read-only APIs, API-backed Daily Trading Cockpit, and first cloud validation are complete.

The active implementation task is now `docs/CURRENT_TASK.md`: complete the next advisory-product sessions by wiring configured public crawler captures into canonical advisory read-model objects, adding the governed LLM extraction/review boundary, promoting outcome review to a first-class object, and extending cloud-visible readiness checks.

## Execution Notes

- Specs remain canonical; this plan is only the current working pointer.
- Keep parallel work disjoint: crawler materialization, LLM boundary tests, outcome journal/read model, and cloud checks may proceed in parallel only when file ownership does not overlap.
- Preserve advisory-only boundaries: no broker integration, no live order placement, no execution endpoints, and no execution UI.
- Cloud deployment validation is required after runtime or deploy-file changes.
