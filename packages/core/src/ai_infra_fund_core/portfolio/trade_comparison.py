from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Mapping

from ai_infra_fund_core.contracts.common import TradeSide
from ai_infra_fund_core.contracts.portfolio import TradeEntry
from ai_infra_fund_core.contracts.signals import TargetWeights


@dataclass(frozen=True, slots=True)
class TradeComparisonResult:
    ticker: str
    current_weight: Decimal
    target_weight: Decimal
    post_trade_weight: Decimal
    trade_weight_delta: Decimal
    is_directionally_aligned: bool
    exceeds_target: bool


def compare_trade_to_target(
    *,
    trade: TradeEntry,
    target_weights: TargetWeights,
    current_weights: Mapping[str, Decimal],
    portfolio_market_value: Decimal,
) -> TradeComparisonResult:
    portfolio_value = Decimal(str(portfolio_market_value))
    if portfolio_value <= Decimal("0"):
        raise ValueError("portfolio_market_value must be positive")
    if trade.price is None:
        raise ValueError("trade price is required for target comparison")

    ticker = trade.ticker.upper()
    current_weight = Decimal(str(current_weights.get(ticker, Decimal("0"))))
    target_weight = Decimal(str(target_weights.weights.get(ticker, Decimal("0"))))
    trade_notional = trade.quantity * trade.price
    raw_delta = trade_notional / portfolio_value
    trade_weight_delta = raw_delta if trade.side is TradeSide.BUY else -raw_delta
    post_trade_weight = current_weight + trade_weight_delta

    if trade.side is TradeSide.BUY:
        is_aligned = target_weight > current_weight and post_trade_weight <= target_weight
        exceeds_target = post_trade_weight > target_weight
    else:
        is_aligned = target_weight < current_weight and post_trade_weight >= target_weight
        exceeds_target = post_trade_weight < target_weight

    return TradeComparisonResult(
        ticker=ticker,
        current_weight=current_weight,
        target_weight=target_weight,
        post_trade_weight=post_trade_weight,
        trade_weight_delta=trade_weight_delta,
        is_directionally_aligned=is_aligned,
        exceeds_target=exceeds_target,
    )
