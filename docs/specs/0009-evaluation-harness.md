# 0009 Evaluation Harness

## Purpose

Define evaluation requirements for models and recommendations.

## Required Checks

- backtests
- walk-forward splits
- lookahead-bias checks
- recursive indicator checks
- Monte Carlo stress
- benchmark comparison
- transaction cost, liquidity, and slippage assumptions
- model shadow-mode comparison

## Model Evaluation Metrics

- schema pass rate
- citation accuracy
- numeric correctness
- contradiction detection
- latency
- cost
- recommendation usefulness

## Rule

Shadow-mode model outputs must not alter production recommendations until explicitly approved.
