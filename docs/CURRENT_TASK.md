# Current Task

## Task

Implement Wave 2 advisory workstation screens from static mock data extracted from the shared planning session.

Wave 2 covers:

1. Daily Trading Cockpit
2. AI Infrastructure Ecosystem Map
3. Live Market / Sentiment Radar
4. Ticker Analyst Workbench
5. Trade Plan Workbench
6. Manual Trade Intents
7. Trade Journal + PnL Review

## Product Objective

Make the AI Infrastructure Trading Analyst Workstation visible as a coherent product while preserving advisory-only guardrails.

This improves:

- catalyst visibility
- segment impact mapping
- equity thesis clarity
- systemic risk awareness
- trade-plan quality
- journal/outcome review usefulness

## Governing Docs

- `AGENTS.md`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`
- `docs/UI_SCREEN_SPECS.md`
- `docs/ANALYST_OBJECT_MODEL.md`
- `docs/specs/0002-trading-policy.md`
- `docs/specs/0003-data-contracts.md`
- `docs/specs/0005-ui-acceptance.md`

## Allowed Files

- `apps/web/**`
- `tests/test_control_room_ui.py`
- `tests/test_wave2_workstation_ui.py`
- `docs/CURRENT_TASK.md`
- `docs/BUILD_LOG.md`

## Forbidden Changes

- no backend changes
- no database changes
- no crawler changes
- no model-router changes
- no dependency changes
- no broker integration
- no live order placement
- no execution endpoints
- no execution-like UI controls
- no backtesting-first UI
- no generic market dashboard widgets
- no LLM-owned scores, risk, constraints, target weights, entry/exit levels, or PnL calculations

## Input Contract

Use static Wave 2 workstation mock data under `apps/web/lib/situational-awareness/`.

## Output Contract

The workstation UI must expose evidence-backed advisory views for:

- market events
- segment impacts
- equity impact assessments
- risk regimes
- suggested advisory actions
- trade plans
- local manual journal review
- deterministic mock PnL review

## Acceptance Criteria

- Daily Trading Cockpit renders static workstation data.
- Segment Map shows first-order and second-order beneficiaries, negatively exposed tickers, risks, events, and evidence.
- Market / Sentiment Radar shows classified intelligence rather than a raw news feed.
- Ticker Analyst Workbench shows thesis, bull/bear case, price scenarios, planning levels, risks, invalidation, and evidence.
- Trade Plan Workbench is planning guidance only.
- Manual Trade Intents remain local journal/planning only.
- Trade Journal + PnL Review uses mock deterministic review values and local journal entry only.
- UI contains no broker connection, order placement, execution, or live trading controls.
- Existing control-room and architecture policy tests pass.

## Tests To Add Or Run

- `./.venv/bin/python -m unittest tests.test_wave2_workstation_ui`
- `./.venv/bin/python -m unittest tests.test_control_room_ui`
- `./.venv/bin/python -m unittest tests.test_architecture_policy`
- `./.venv/bin/python -m unittest discover -s tests`
- `python3 -m compileall packages services tests`
- `npm run build --prefix apps/web`
- `npm audit --omit=dev --prefix apps/web`
- `git diff --check`

## Definition Of Done

- Wave 2 screens implemented from static mock data.
- Relevant UI and policy tests pass.
- Frontend build and audit pass.
- `docs/BUILD_LOG.md` updated.
- Changes committed and pushed.
- Cloud frontend deployed and validated if deployment credentials are available.
- Remaining gaps documented.
