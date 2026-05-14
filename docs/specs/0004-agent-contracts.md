# 0004 Agent Contracts

## Purpose

Define allowed agent and LLM responsibilities.

## Rule

LLMs interpret evidence and explain recommendations. Deterministic code computes scores, risk, backtests, constraints, and target weights.

## Allowed LLM Tasks

- source classification
- ticker/theme tagging
- evidence summarization
- claim extraction
- contradiction detection
- recommendation narrative drafting
- adversarial review
- schema repair and validation retries

## Forbidden LLM Tasks

- final numeric score generation
- direct TargetWeights generation
- portfolio constraint bypass
- live order creation
- unapproved private data exfiltration

## Required Outputs

Every model-assisted action must create a `ModelRun` record with model identity, deployment, prompt version, input hash, output hash, schema validity, retry count, and latency when available.
