# Current Task

## Task

Redesign the Value-Chain Atlas screen into a segment-by-subtheme investment
candidate matrix with an AI Grid default lens.

## Product Objective

Improve advisory brief usefulness, segment impact mapping, and equity thesis
quality by making each AI infrastructure subsegment show its configured
candidate tickers, watchlist priority, current advisory stance, evidence
coverage, and risk/invalidation context.

## Governing Docs And Specs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/CURRENT_TASK.md`

## Allowed Files

- `apps/web/app/themes/page.tsx`
- `apps/web/components/`
- `apps/web/app/globals.css`
- `apps/web/lib/value-chain.ts`
- `apps/web/lib/watchlist-mirror.ts`
- `apps/web/lib/advisory/workstation-data.ts`
- focused frontend/UI tests under `tests/`
- `docs/BUILD_LOG.md`
- `docs/CURRENT_TASK.md`

## Forbidden Changes

- no broker integration
- no live order placement
- no order routing
- no execution endpoints
- no execution UI
- no automated trading loops
- no dependency changes
- no new backend endpoint unless existing read models are insufficient
- no execution-like "must buy" language in UI labels

## Acceptance Criteria

- `/themes` is repositioned as a Value-Chain Candidate Matrix, not a vague
  static atlas.
- AI Grid is the default lens and surfaces power/grid/datacenter-power
  candidates by subtheme.
- Candidate rows include ticker, company, watchlist priority, current advisory
  stance, latest change, risk/invalidation context, evidence count, and ticker
  workbench link.
- Existing advisory labels are used: `accumulate`, `watch`, `hold`, `review`,
  `trim`, `avoid`, and `exit-candidate`.
- Existing read-only API feeds and watchlist taxonomy are reused; UI does not
  contain scoring or portfolio business logic.
- No broker, order, execution, or automated-trading surface is introduced.

## Tests To Run

```bash
./.venv/bin/python -m unittest tests.test_wave2_workstation_ui
./.venv/bin/python -m unittest tests.test_watchlist_frontend_parity tests.test_control_room_ui tests.test_wave2_workstation_ui
npm --prefix apps/web run build
git diff --check
```

## Definition Of Done

- RED test is confirmed before production code changes.
- Targeted frontend tests pass.
- Next build passes.
- `git diff --check` passes.
- `docs/BUILD_LOG.md` records the redesign and verification.
- Any unrelated dirty worktree state is reported explicitly.
