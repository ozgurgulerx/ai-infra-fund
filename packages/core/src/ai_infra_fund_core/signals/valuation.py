from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from ai_infra_fund_core.contracts.common import (
    require_aware_datetime,
    require_decimal_range,
    require_non_negative,
    require_positive,
    require_text,
)

from .formulas import FORMULA_VERSIONS, SCORE_QUANT


ZERO = Decimal("0")
ONE = Decimal("1")
MONEY_QUANT = Decimal("0.001")


@dataclass(frozen=True, slots=True)
class ValuationInputs:
    market_cap: Decimal
    free_cash_flow: Decimal
    growth_rate: Decimal
    discount_rate: Decimal
    terminal_growth_rate: Decimal
    net_income: Decimal
    depreciation_and_amortization: Decimal
    capex: Decimal
    working_capital_change: Decimal
    ebitda: Decimal
    peer_ev_ebitda_multiple: Decimal
    net_debt: Decimal
    book_value: Decimal
    cost_of_equity: Decimal
    return_on_equity: Decimal
    margin_of_safety: Decimal
    forecast_years: int = 5

    def __post_init__(self) -> None:
        object.__setattr__(self, "market_cap", require_positive(self.market_cap, "market_cap"))
        object.__setattr__(self, "free_cash_flow", require_positive(self.free_cash_flow, "free_cash_flow"))
        object.__setattr__(self, "growth_rate", Decimal(str(self.growth_rate)))
        object.__setattr__(self, "discount_rate", require_positive(self.discount_rate, "discount_rate"))
        object.__setattr__(self, "terminal_growth_rate", Decimal(str(self.terminal_growth_rate)))
        if self.discount_rate <= self.terminal_growth_rate:
            raise ValueError("discount_rate must exceed terminal_growth_rate")
        object.__setattr__(self, "net_income", require_positive(self.net_income, "net_income"))
        object.__setattr__(
            self,
            "depreciation_and_amortization",
            require_non_negative(self.depreciation_and_amortization, "depreciation_and_amortization"),
        )
        object.__setattr__(self, "capex", require_non_negative(self.capex, "capex"))
        object.__setattr__(self, "working_capital_change", Decimal(str(self.working_capital_change)))
        object.__setattr__(self, "ebitda", require_positive(self.ebitda, "ebitda"))
        object.__setattr__(
            self,
            "peer_ev_ebitda_multiple",
            require_positive(self.peer_ev_ebitda_multiple, "peer_ev_ebitda_multiple"),
        )
        object.__setattr__(self, "net_debt", Decimal(str(self.net_debt)))
        object.__setattr__(self, "book_value", require_positive(self.book_value, "book_value"))
        object.__setattr__(self, "cost_of_equity", require_positive(self.cost_of_equity, "cost_of_equity"))
        if self.cost_of_equity <= self.terminal_growth_rate:
            raise ValueError("cost_of_equity must exceed terminal_growth_rate")
        object.__setattr__(self, "return_on_equity", Decimal(str(self.return_on_equity)))
        object.__setattr__(
            self,
            "margin_of_safety",
            require_decimal_range(self.margin_of_safety, "margin_of_safety", ZERO, ONE),
        )
        if self.forecast_years <= 0:
            raise ValueError("forecast_years must be positive")


@dataclass(frozen=True, slots=True)
class ValuationSnapshot:
    ticker: str
    as_of: datetime
    dcf_value: Decimal
    owner_earnings_value: Decimal
    ev_ebitda_value: Decimal
    residual_income_value: Decimal
    weighted_intrinsic_value: Decimal
    valuation_gap: Decimal
    valuation_score: Decimal
    valuation_label: str
    formula_version: str
    score_breakdown: dict[str, str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "formula_version", require_text(self.formula_version, "formula_version"))


def compute_valuation_snapshot(*, ticker: str, as_of: datetime, inputs: ValuationInputs) -> ValuationSnapshot:
    require_aware_datetime(as_of, "as_of")
    dcf_value = _discounted_cash_flow_value(
        free_cash_flow=inputs.free_cash_flow,
        growth_rate=inputs.growth_rate,
        discount_rate=inputs.discount_rate,
        terminal_growth_rate=inputs.terminal_growth_rate,
        forecast_years=inputs.forecast_years,
    )
    owner_earnings_value = _owner_earnings_value(inputs)
    ev_ebitda_value = _ev_ebitda_value(inputs)
    residual_income_value = _residual_income_value(inputs)
    weighted_intrinsic_value = _quantize_money(
        dcf_value * Decimal("0.35")
        + owner_earnings_value * Decimal("0.35")
        + ev_ebitda_value * Decimal("0.20")
        + residual_income_value * Decimal("0.10")
    )
    valuation_gap = _quantize_score(weighted_intrinsic_value / inputs.market_cap - ONE)
    valuation_score = _quantize_score(_clamp(Decimal("0.5") + valuation_gap, ZERO, ONE))

    return ValuationSnapshot(
        ticker=ticker,
        as_of=as_of,
        dcf_value=dcf_value,
        owner_earnings_value=owner_earnings_value,
        ev_ebitda_value=ev_ebitda_value,
        residual_income_value=residual_income_value,
        weighted_intrinsic_value=weighted_intrinsic_value,
        valuation_gap=valuation_gap,
        valuation_score=valuation_score,
        valuation_label=_valuation_label(valuation_gap, inputs.margin_of_safety),
        formula_version=FORMULA_VERSIONS["valuation_score"],
        score_breakdown={
            "dcf_value": str(dcf_value),
            "owner_earnings_value": str(owner_earnings_value),
            "ev_ebitda_value": str(ev_ebitda_value),
            "residual_income_value": str(residual_income_value),
            "weighted_intrinsic_value": str(weighted_intrinsic_value),
            "valuation_gap": str(valuation_gap),
            "valuation_score": str(valuation_score),
        },
    )


def _discounted_cash_flow_value(
    *,
    free_cash_flow: Decimal,
    growth_rate: Decimal,
    discount_rate: Decimal,
    terminal_growth_rate: Decimal,
    forecast_years: int,
) -> Decimal:
    present_value = ZERO
    for year in range(1, forecast_years + 1):
        projected_fcf = free_cash_flow * (ONE + growth_rate) ** year
        present_value += projected_fcf / (ONE + discount_rate) ** year
    final_fcf = free_cash_flow * (ONE + growth_rate) ** forecast_years
    terminal_value = final_fcf * (ONE + terminal_growth_rate) / (discount_rate - terminal_growth_rate)
    present_value += terminal_value / (ONE + discount_rate) ** forecast_years
    return _quantize_money(present_value)


def _owner_earnings_value(inputs: ValuationInputs) -> Decimal:
    owner_earnings = (
        inputs.net_income
        + inputs.depreciation_and_amortization
        - inputs.capex
        - inputs.working_capital_change
    )
    if owner_earnings <= ZERO:
        return ZERO
    value = _discounted_cash_flow_value(
        free_cash_flow=owner_earnings,
        growth_rate=inputs.growth_rate,
        discount_rate=inputs.discount_rate,
        terminal_growth_rate=inputs.terminal_growth_rate,
        forecast_years=inputs.forecast_years,
    )
    return _quantize_money(value * (ONE - inputs.margin_of_safety))


def _ev_ebitda_value(inputs: ValuationInputs) -> Decimal:
    return _quantize_money(max(ZERO, inputs.ebitda * inputs.peer_ev_ebitda_multiple - inputs.net_debt))


def _residual_income_value(inputs: ValuationInputs) -> Decimal:
    residual_income = inputs.book_value * (inputs.return_on_equity - inputs.cost_of_equity)
    if residual_income == ZERO:
        return _quantize_money(inputs.book_value)

    present_value = inputs.book_value
    for year in range(1, inputs.forecast_years + 1):
        projected_residual_income = residual_income * (ONE + inputs.growth_rate) ** year
        present_value += projected_residual_income / (ONE + inputs.cost_of_equity) ** year
    final_residual_income = residual_income * (ONE + inputs.growth_rate) ** inputs.forecast_years
    terminal_value = final_residual_income * (ONE + inputs.terminal_growth_rate) / (
        inputs.cost_of_equity - inputs.terminal_growth_rate
    )
    present_value += terminal_value / (ONE + inputs.cost_of_equity) ** inputs.forecast_years
    return _quantize_money(max(ZERO, present_value))


def _valuation_label(gap: Decimal, margin_of_safety: Decimal) -> str:
    threshold = max(Decimal("0.10"), margin_of_safety)
    if gap >= threshold:
        return "undervalued"
    if gap <= -threshold:
        return "overvalued"
    return "fairly_valued"


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(high, max(low, value))


def _quantize_score(value: Decimal) -> Decimal:
    return value.quantize(Decimal(SCORE_QUANT), rounding=ROUND_HALF_UP).normalize()


def _quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP).normalize()
