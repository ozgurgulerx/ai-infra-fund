# Current Task

## Task

Build the Daily Situational Awareness Brief screen from static mock data.

## Product Objective

Make the AI Infrastructure Situational Awareness Analyst visible as a coherent product.

This improves:

- daily analyst brief usefulness
- catalyst visibility
- segment impact mapping
- equity thesis clarity
- systemic risk awareness

## Governing Specs

- `docs/UI_SCREEN_SPECS.md`
- `docs/mock_data/situational_awareness_brief.example.json`
- `docs/PRODUCT.md`
- `docs/ARCHITECTURE.md`
- `docs/ALPHA_ANALYST_PRINCIPLES.md`

## Allowed Files

- `apps/web/**`
- `docs/BUILD_LOG.md`

## Forbidden Changes

- no backend changes
- no database changes
- no crawler changes
- no model-router changes
- no scoring implementation
- no broker integration
- no order placement UI
- no backtesting UI
- no generic stock dashboard widgets

## Input Contract

Read static mock data from:

- `docs/mock_data/situational_awareness_brief.example.json`

The UI must treat the mock data as read-only. Do not create API calls or backend endpoints for this task.

## Output Contract

Render a Daily Situational Awareness Brief screen that follows `docs/UI_SCREEN_SPECS.md` section `1. Daily Situational Awareness Brief`.

The screen must show:

- executive summary
- top `MarketEvent`s
- segment impacts
- equity impact assessments
- risk regime updates
- evidence references
- risk flags
- invalidation conditions
- analyst actions: watch, accumulate, hold, trim, avoid

## Acceptance Criteria

- Daily Brief screen renders from static mock JSON.
- Shows executive summary.
- Shows top `MarketEvent`s.
- Shows segment impacts.
- Shows equity impact assessments.
- Shows risk regime updates.
- Shows evidence references.
- Shows risk flags and invalidation conditions.
- Uses analyst actions: watch, accumulate, hold, trim, avoid.
- No buy/sell execution controls.
- No broker controls or broker integration.
- No order placement UI.
- No backtesting UI.
- No generic stock dashboard widgets.
- No marketing-page style; the screen must feel like an analyst control room.

## Tests To Add Or Run

- `git diff --check`
- frontend build command if configured, expected to be `npm run build --prefix apps/web`
- existing UI tests if configured

## Definition Of Done

- screen renders from mock data
- no unrelated files changed
- `docs/BUILD_LOG.md` updated
