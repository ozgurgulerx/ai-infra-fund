from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_non_negative, require_positive, require_text

from .formulas import SCORE_QUANT


ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class FundamentalPeriodSnapshot:
    period_end: datetime
    revenue: Decimal
    operating_margin: Decimal
    valuation_multiple: Decimal
    guidance_revenue_growth: Decimal
    capex_to_revenue: Decimal
    debt_to_equity: Decimal
    cash_to_debt: Decimal
    eps_actual: Decimal
    eps_consensus: Decimal

    def __post_init__(self) -> None:
        require_aware_datetime(self.period_end, "period_end")
        object.__setattr__(self, "revenue", require_positive(self.revenue, "revenue"))
        object.__setattr__(self, "valuation_multiple", require_positive(self.valuation_multiple, "valuation_multiple"))
        object.__setattr__(self, "capex_to_revenue", require_non_negative(self.capex_to_revenue, "capex_to_revenue"))
        object.__setattr__(self, "debt_to_equity", require_non_negative(self.debt_to_equity, "debt_to_equity"))
        object.__setattr__(self, "cash_to_debt", require_non_negative(self.cash_to_debt, "cash_to_debt"))


@dataclass(frozen=True, slots=True)
class FundamentalSnapshot:
    ticker: str
    as_of: datetime
    revenue_growth: Decimal
    margin_trend: Decimal
    valuation_pressure: Decimal
    guidance_direction: str
    capex_exposure: Decimal
    balance_sheet_risk: Decimal
    earnings_surprise: Decimal
    fundamental_score: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")


def compute_fundamental_snapshot(
    *,
    ticker: str,
    as_of: datetime,
    periods: Sequence[FundamentalPeriodSnapshot],
    benchmark_valuation_multiple: Decimal,
) -> FundamentalSnapshot:
    require_aware_datetime(as_of, "as_of")
    benchmark = require_positive(benchmark_valuation_multiple, "benchmark_valuation_multiple")
    history = tuple(sorted((period for period in periods if period.period_end <= as_of), key=lambda period: period.period_end))
    if not history:
        raise ValueError("at least one point-in-time fundamental period is required")

    latest = history[-1]
    prior = history[-2] if len(history) > 1 else latest
    revenue_growth = latest.revenue / prior.revenue - ONE if prior.revenue > ZERO and latest is not prior else ZERO
    margin_trend = latest.operating_margin - prior.operating_margin if latest is not prior else ZERO
    valuation_pressure = _clamp((latest.valuation_multiple / benchmark) - ONE, ZERO, ONE)
    balance_sheet_risk = _clamp(latest.debt_to_equity * Decimal("0.4") + max(ZERO, ONE - latest.cash_to_debt) * Decimal("0.4"), ZERO, ONE)
    earnings_surprise = _earnings_surprise(latest.eps_actual, latest.eps_consensus)
    fundamental_score = _fundamental_score(
        revenue_growth=revenue_growth,
        margin_trend=margin_trend,
        guidance_revenue_growth=latest.guidance_revenue_growth,
        valuation_pressure=valuation_pressure,
        capex_exposure=latest.capex_to_revenue,
        balance_sheet_risk=balance_sheet_risk,
        earnings_surprise=earnings_surprise,
    )

    return FundamentalSnapshot(
        ticker=ticker,
        as_of=as_of,
        revenue_growth=_quantize(revenue_growth),
        margin_trend=_quantize(margin_trend),
        valuation_pressure=_quantize(valuation_pressure),
        guidance_direction=_direction_label(latest.guidance_revenue_growth),
        capex_exposure=_quantize(latest.capex_to_revenue),
        balance_sheet_risk=_quantize(balance_sheet_risk),
        earnings_surprise=_quantize(earnings_surprise),
        fundamental_score=fundamental_score,
    )


def _earnings_surprise(actual: Decimal, consensus: Decimal) -> Decimal:
    consensus_value = Decimal(str(consensus))
    if consensus_value == ZERO:
        return ZERO
    return (Decimal(str(actual)) - consensus_value) / abs(consensus_value)


def _fundamental_score(
    *,
    revenue_growth: Decimal,
    margin_trend: Decimal,
    guidance_revenue_growth: Decimal,
    valuation_pressure: Decimal,
    capex_exposure: Decimal,
    balance_sheet_risk: Decimal,
    earnings_surprise: Decimal,
) -> Decimal:
    score = (
        _unit_score(revenue_growth, Decimal("2")) * Decimal("0.25")
        + _unit_score(margin_trend, Decimal("5")) * Decimal("0.15")
        + _unit_score(guidance_revenue_growth, Decimal("5")) * Decimal("0.15")
        + _unit_score(earnings_surprise, Decimal("5")) * Decimal("0.15")
        + (ONE - valuation_pressure) * Decimal("0.15")
        + (ONE - balance_sheet_risk) * Decimal("0.10")
        + (ONE - _clamp(capex_exposure, ZERO, ONE)) * Decimal("0.05")
    )
    return _quantize(_clamp(score, ZERO, ONE))


def _unit_score(delta: Decimal, scale: Decimal) -> Decimal:
    return _clamp(Decimal("0.5") + delta * scale, ZERO, ONE)


def _direction_label(value: Decimal) -> str:
    if value >= Decimal("0.01"):
        return "positive"
    if value <= Decimal("-0.01"):
        return "negative"
    return "neutral"


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(high, max(low, value))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal(SCORE_QUANT), rounding=ROUND_HALF_UP).normalize()
