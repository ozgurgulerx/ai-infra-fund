from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Mapping, Sequence

from ai_infra_fund_core.contracts.common import stable_hash_payload
from ai_infra_fund_core.contracts.signals import SignalBundle, TargetWeights

from .constraints import (
    ONE,
    ZERO,
    PortfolioConstraints,
    constraints_to_dict,
    validate_portfolio_constraints,
)


ENGINE_ID = "deterministic_portfolio_engine.v1"
WEIGHT_QUANT = Decimal("0.0001")


def generate_target_weights(
    *,
    portfolio_id: str,
    signals: Sequence[SignalBundle],
    constraints: PortfolioConstraints,
    as_of: datetime,
    created_at: datetime,
    theme_by_ticker: Mapping[str, str] | None = None,
    liquidity_by_ticker: Mapping[str, Decimal] | None = None,
    current_weights: Mapping[str, Decimal] | None = None,
    current_cash_weight: Decimal | None = None,
) -> TargetWeights:
    eligible_signals = _eligible_signals(signals, constraints, liquidity_by_ticker or {})
    if not eligible_signals:
        raise ValueError("at least one signal with sufficient liquidity is required")

    raw_weights = _raw_target_weights(eligible_signals, constraints.cash_floor)
    capped_weights = _apply_single_name_cap(raw_weights, constraints.max_single_name_weight)
    themed_weights = _apply_theme_cap(capped_weights, constraints, theme_by_ticker or {})
    cash_weight = _cash_from_weights(themed_weights)

    adjusted_weights, adjusted_cash = _apply_turnover_cap(
        weights=themed_weights,
        cash_weight=cash_weight,
        constraints=constraints,
        current_weights=current_weights or {},
        current_cash_weight=current_cash_weight,
    )
    final_weights, final_cash = _finalize_sum(adjusted_weights, adjusted_cash)

    validation = validate_portfolio_constraints(
        weights=final_weights,
        cash_weight=final_cash,
        constraints=constraints,
        theme_by_ticker=theme_by_ticker,
        liquidity_by_ticker=liquidity_by_ticker,
        current_weights=current_weights,
        current_cash_weight=current_cash_weight,
    )
    if not validation.passed:
        raise ValueError(f"generated target weights failed constraints: {validation.violation_codes}")

    source_signal_bundle_ids = tuple(signal.signal_bundle_id for signal in eligible_signals)
    return TargetWeights(
        target_weights_id=_target_weights_id(
            portfolio_id=portfolio_id,
            as_of=as_of,
            weights=final_weights,
            cash_weight=final_cash,
            source_signal_bundle_ids=source_signal_bundle_ids,
            constraints=constraints,
        ),
        as_of=as_of,
        portfolio_id=portfolio_id,
        cash_weight=final_cash,
        weights=final_weights,
        constraints={
            **constraints_to_dict(constraints),
            "turnover": str(validation.turnover),
            "formula_version": "v1",
        },
        source_signal_bundle_ids=source_signal_bundle_ids,
        generated_by=ENGINE_ID,
        validation_status="validated",
        created_at=created_at,
    )


def _eligible_signals(
    signals: Sequence[SignalBundle],
    constraints: PortfolioConstraints,
    liquidity_by_ticker: Mapping[str, Decimal],
) -> tuple[SignalBundle, ...]:
    eligible: list[SignalBundle] = []
    for signal in signals:
        liquidity = liquidity_by_ticker.get(signal.ticker)
        if liquidity is not None and Decimal(str(liquidity)) < constraints.liquidity_floor:
            continue
        eligible.append(signal)
    return tuple(eligible)


def _raw_target_weights(signals: Sequence[SignalBundle], cash_floor: Decimal) -> dict[str, Decimal]:
    scores = {signal.ticker: _attractiveness_score(signal) for signal in signals}
    total_score = sum(scores.values(), ZERO)
    if total_score <= ZERO:
        raise ValueError("at least one positive signal score is required")
    equity_budget = ONE - cash_floor
    return {
        ticker: _quantize((score / total_score) * equity_budget)
        for ticker, score in scores.items()
    }


def _attractiveness_score(signal: SignalBundle) -> Decimal:
    return max(
        ZERO,
        signal.strategic_thesis_score * Decimal("0.45")
        + signal.tactical_technical_score * Decimal("0.25")
        + signal.forward_indicator_score * Decimal("0.20")
        + (ONE - signal.portfolio_risk_score) * Decimal("0.10"),
    )


def _apply_single_name_cap(weights: Mapping[str, Decimal], max_weight: Decimal) -> dict[str, Decimal]:
    return {ticker: min(weight, max_weight) for ticker, weight in weights.items()}


def _apply_theme_cap(
    weights: Mapping[str, Decimal],
    constraints: PortfolioConstraints,
    theme_by_ticker: Mapping[str, str],
) -> dict[str, Decimal]:
    adjusted = dict(weights)
    theme_totals: dict[str, Decimal] = {}
    for ticker, weight in adjusted.items():
        theme = theme_by_ticker.get(ticker)
        if theme:
            theme_totals[theme] = theme_totals.get(theme, ZERO) + weight

    for theme, total in theme_totals.items():
        if total <= constraints.max_theme_exposure:
            continue
        scale = constraints.max_theme_exposure / total
        for ticker, weight in tuple(adjusted.items()):
            if theme_by_ticker.get(ticker) == theme:
                adjusted[ticker] = _quantize(weight * scale)
    return adjusted


def _apply_turnover_cap(
    *,
    weights: Mapping[str, Decimal],
    cash_weight: Decimal,
    constraints: PortfolioConstraints,
    current_weights: Mapping[str, Decimal],
    current_cash_weight: Decimal | None,
) -> tuple[dict[str, Decimal], Decimal]:
    validation = validate_portfolio_constraints(
        weights=weights,
        cash_weight=cash_weight,
        constraints=PortfolioConstraints(
            max_single_name_weight=ONE,
            max_theme_exposure=ONE,
            cash_floor=ZERO,
            liquidity_floor=ZERO,
            turnover_cap=constraints.turnover_cap,
        ),
        current_weights=current_weights,
        current_cash_weight=current_cash_weight,
    )
    if validation.passed or validation.turnover == ZERO:
        return dict(weights), cash_weight

    ratio = constraints.turnover_cap / validation.turnover
    current_cash = Decimal(str(current_cash_weight or ZERO))
    tickers = set(weights) | {str(ticker).upper() for ticker in current_weights}
    adjusted = {
        ticker: _quantize(
            Decimal(str(current_weights.get(ticker, ZERO))) + (weights.get(ticker, ZERO) - Decimal(str(current_weights.get(ticker, ZERO)))) * ratio
        )
        for ticker in tickers
    }
    adjusted_cash = _quantize(current_cash + (cash_weight - current_cash) * ratio)
    return {ticker: weight for ticker, weight in adjusted.items() if weight > ZERO}, adjusted_cash


def _finalize_sum(weights: Mapping[str, Decimal], cash_weight: Decimal) -> tuple[dict[str, Decimal], Decimal]:
    cleaned = {ticker: _quantize(weight) for ticker, weight in weights.items() if weight > ZERO}
    cash = _quantize(cash_weight)
    total = cash + sum(cleaned.values(), ZERO)
    if total != ONE:
        cash = _quantize(cash + (ONE - total))
    return cleaned, cash


def _cash_from_weights(weights: Mapping[str, Decimal]) -> Decimal:
    return _quantize(ONE - sum(weights.values(), ZERO))


def _target_weights_id(
    *,
    portfolio_id: str,
    as_of: datetime,
    weights: Mapping[str, Decimal],
    cash_weight: Decimal,
    source_signal_bundle_ids: tuple[str, ...],
    constraints: PortfolioConstraints,
) -> str:
    digest = stable_hash_payload(
        {
            "portfolio_id": portfolio_id,
            "as_of": as_of,
            "weights": dict(sorted(weights.items())),
            "cash_weight": cash_weight,
            "source_signal_bundle_ids": source_signal_bundle_ids,
            "constraints": constraints_to_dict(constraints),
            "engine": ENGINE_ID,
        }
    )
    return f"target-weights-{digest[:16]}"


def _quantize(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(WEIGHT_QUANT, rounding=ROUND_HALF_UP).normalize()
