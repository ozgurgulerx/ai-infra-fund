from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import statistics
from typing import Sequence

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_positive, require_text

from .formulas import SCORE_QUANT
from .scoring import TacticalTechnicalInputs, score_tactical_technical


ZERO = Decimal("0")
ONE = Decimal("1")


@dataclass(frozen=True, slots=True)
class MarketPoint:
    as_of: datetime
    close: Decimal
    volume: Decimal

    def __post_init__(self) -> None:
        require_aware_datetime(self.as_of, "as_of")
        object.__setattr__(self, "close", require_positive(self.close, "close"))
        object.__setattr__(self, "volume", require_positive(self.volume, "volume"))


@dataclass(frozen=True, slots=True)
class TechnicalSnapshot:
    ticker: str
    as_of: datetime
    short_moving_average: Decimal
    long_moving_average: Decimal
    momentum: Decimal
    trend_strength: Decimal
    volatility: Decimal
    rsi_score: Decimal
    drawdown: Decimal
    volume_confirmation: Decimal
    tactical_technical_score: Decimal

    def __post_init__(self) -> None:
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        require_aware_datetime(self.as_of, "as_of")


def compute_technical_snapshot(
    *,
    ticker: str,
    as_of: datetime,
    points: Sequence[MarketPoint],
    short_window: int = 5,
    long_window: int = 10,
    momentum_window: int = 5,
    rsi_window: int = 14,
) -> TechnicalSnapshot:
    require_aware_datetime(as_of, "as_of")
    if short_window <= 0 or long_window <= 0 or momentum_window <= 0 or rsi_window <= 0:
        raise ValueError("technical windows must be positive")

    history = tuple(sorted((point for point in points if point.as_of <= as_of), key=lambda point: point.as_of))
    if not history:
        raise ValueError("at least one point-in-time market snapshot is required")

    closes = tuple(point.close for point in history)
    volumes = tuple(point.volume for point in history)
    latest_close = closes[-1]
    short_ma = _average(closes[-short_window:])
    long_ma = _average(closes[-long_window:])
    momentum = _momentum(closes, momentum_window)
    trend_strength = _trend_strength(short_ma, long_ma)
    momentum_score = _unit_score(momentum, Decimal("2"))
    volatility = _volatility(closes[-long_window:])
    rsi_score = _rsi_score(closes[-(rsi_window + 1):])
    drawdown = (latest_close / max(closes) - ONE) if max(closes) > ZERO else ZERO
    volume_confirmation = _volume_confirmation(volumes[-long_window:])
    tactical_score = score_tactical_technical(
        TacticalTechnicalInputs(
            trend_strength=trend_strength,
            momentum=momentum_score,
            relative_strength=rsi_score,
            volume_confirmation=volume_confirmation,
        )
    )

    return TechnicalSnapshot(
        ticker=ticker,
        as_of=as_of,
        short_moving_average=_quantize_market(short_ma),
        long_moving_average=_quantize_market(long_ma),
        momentum=_quantize(momentum),
        trend_strength=trend_strength,
        volatility=volatility,
        rsi_score=rsi_score,
        drawdown=_quantize(drawdown),
        volume_confirmation=volume_confirmation,
        tactical_technical_score=tactical_score,
    )


def _average(values: Sequence[Decimal]) -> Decimal:
    return sum(values, ZERO) / Decimal(len(values))


def _momentum(closes: Sequence[Decimal], window: int) -> Decimal:
    if len(closes) <= window:
        base = closes[0]
    else:
        base = closes[-(window + 1)]
    return closes[-1] / base - ONE


def _trend_strength(short_ma: Decimal, long_ma: Decimal) -> Decimal:
    if long_ma <= ZERO:
        return Decimal("0.5")
    return _quantize(_unit_score(short_ma / long_ma - ONE, Decimal("5")))


def _unit_score(delta: Decimal, scale: Decimal) -> Decimal:
    return _clamp(Decimal("0.5") + delta * scale, ZERO, ONE)


def _volatility(closes: Sequence[Decimal]) -> Decimal:
    if len(closes) < 3:
        return ZERO
    returns = [float(closes[index] / closes[index - 1] - ONE) for index in range(1, len(closes))]
    return _quantize(Decimal(str(statistics.pstdev(returns))))


def _rsi_score(closes: Sequence[Decimal]) -> Decimal:
    if len(closes) < 2:
        return Decimal("0.5")
    gains: list[Decimal] = []
    losses: list[Decimal] = []
    for index in range(1, len(closes)):
        change = closes[index] - closes[index - 1]
        if change > ZERO:
            gains.append(change)
        elif change < ZERO:
            losses.append(abs(change))
    total_gain = sum(gains, ZERO)
    total_loss = sum(losses, ZERO)
    if total_gain == ZERO and total_loss == ZERO:
        return Decimal("0.5")
    if total_loss == ZERO:
        return ONE
    return _quantize(total_gain / (total_gain + total_loss))


def _volume_confirmation(volumes: Sequence[Decimal]) -> Decimal:
    average_volume = _average(volumes)
    if average_volume <= ZERO:
        return Decimal("0.5")
    return _quantize(_clamp(Decimal("0.5") + ((volumes[-1] / average_volume) - ONE) * Decimal("0.5"), ZERO, ONE))


def _clamp(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    return min(high, max(low, value))


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(Decimal(SCORE_QUANT), rounding=ROUND_HALF_UP).normalize()


def _quantize_market(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP).normalize()
