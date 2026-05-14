from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0")
ONE = Decimal("1")
BPS = Decimal("10000")
MONEY_QUANT = Decimal("0.000001")


@dataclass(frozen=True, slots=True)
class TransactionCostAssumptions:
    spread_bps: Decimal = ZERO
    slippage_bps: Decimal = ZERO
    fee_per_trade: Decimal = ZERO
    fee_rate_bps: Decimal = ZERO

    def __post_init__(self) -> None:
        for field_name in ("spread_bps", "slippage_bps", "fee_per_trade", "fee_rate_bps"):
            object.__setattr__(self, field_name, _non_negative(getattr(self, field_name), field_name))


@dataclass(frozen=True, slots=True)
class TransactionCostEstimate:
    ticker: str
    quantity: Decimal
    price: Decimal
    notional: Decimal
    spread_cost: Decimal
    slippage_cost: Decimal
    fees: Decimal
    total_cost: Decimal
    cost_bps: Decimal


@dataclass(frozen=True, slots=True)
class CapacityAssumptions:
    average_daily_volume: Decimal
    max_participation_rate: Decimal
    minimum_average_daily_volume: Decimal = ZERO

    def __post_init__(self) -> None:
        object.__setattr__(self, "average_daily_volume", _positive(self.average_daily_volume, "average_daily_volume"))
        object.__setattr__(
            self,
            "max_participation_rate",
            _unit_positive(self.max_participation_rate, "max_participation_rate"),
        )
        object.__setattr__(
            self,
            "minimum_average_daily_volume",
            _non_negative(self.minimum_average_daily_volume, "minimum_average_daily_volume"),
        )


@dataclass(frozen=True, slots=True)
class CapacityValidationResult:
    ticker: str
    passed: bool
    violation_codes: tuple[str, ...]
    quantity: Decimal
    price: Decimal
    order_notional: Decimal
    average_daily_volume: Decimal
    allowed_quantity: Decimal
    participation_rate: Decimal


def estimate_transaction_cost(
    *,
    ticker: str,
    quantity: Decimal,
    price: Decimal,
    assumptions: TransactionCostAssumptions,
) -> TransactionCostEstimate:
    normalized_ticker = _ticker(ticker)
    normalized_quantity = _positive(quantity, "quantity")
    normalized_price = _positive(price, "price")
    notional = _quantize(normalized_quantity * normalized_price)
    spread_cost = _quantize(notional * assumptions.spread_bps / BPS)
    slippage_cost = _quantize(notional * assumptions.slippage_bps / BPS)
    fees = _quantize(assumptions.fee_per_trade + (notional * assumptions.fee_rate_bps / BPS))
    total_cost = _quantize(spread_cost + slippage_cost + fees)
    cost_bps = _quantize(total_cost / notional * BPS)

    return TransactionCostEstimate(
        ticker=normalized_ticker,
        quantity=_quantize(normalized_quantity),
        price=_quantize(normalized_price),
        notional=notional,
        spread_cost=spread_cost,
        slippage_cost=slippage_cost,
        fees=fees,
        total_cost=total_cost,
        cost_bps=cost_bps,
    )


def validate_capacity(
    *,
    ticker: str,
    quantity: Decimal,
    price: Decimal,
    assumptions: CapacityAssumptions,
) -> CapacityValidationResult:
    normalized_ticker = _ticker(ticker)
    normalized_quantity = _positive(quantity, "quantity")
    normalized_price = _positive(price, "price")
    participation_rate = _quantize(normalized_quantity / assumptions.average_daily_volume)
    allowed_quantity = _quantize(assumptions.average_daily_volume * assumptions.max_participation_rate)
    order_notional = _quantize(normalized_quantity * normalized_price)

    violations: list[str] = []
    if assumptions.average_daily_volume < assumptions.minimum_average_daily_volume:
        violations.append("minimum_average_daily_volume")
    if participation_rate > assumptions.max_participation_rate:
        violations.append("max_participation_rate")

    violation_codes = tuple(dict.fromkeys(violations))
    return CapacityValidationResult(
        ticker=normalized_ticker,
        passed=not violation_codes,
        violation_codes=violation_codes,
        quantity=_quantize(normalized_quantity),
        price=_quantize(normalized_price),
        order_notional=order_notional,
        average_daily_volume=_quantize(assumptions.average_daily_volume),
        allowed_quantity=allowed_quantity,
        participation_rate=participation_rate,
    )


def _ticker(value: str) -> str:
    ticker = str(value).strip().upper()
    if not ticker:
        raise ValueError("ticker is required")
    return ticker


def _positive(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value <= ZERO:
        raise ValueError(f"{field_name} must be positive")
    return decimal_value


def _non_negative(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < ZERO:
        raise ValueError(f"{field_name} must be non-negative")
    return decimal_value


def _unit_positive(value: Decimal, field_name: str) -> Decimal:
    decimal_value = _positive(value, field_name)
    if decimal_value > ONE:
        raise ValueError(f"{field_name} must be between 0 and 1")
    return decimal_value


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)
