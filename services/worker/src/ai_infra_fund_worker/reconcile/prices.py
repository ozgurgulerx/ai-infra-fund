from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable, Iterable

from ai_infra_fund_core.audit.experiment_events import ExperimentEvent, build_event
from ai_infra_fund_core.equity_intelligence.connectors import MarketPriceSnapshot


_DEFAULT_THRESHOLD = Decimal("0.005")


def detect_price_disagreement(
    *,
    yfinance: MarketPriceSnapshot,
    stooq: MarketPriceSnapshot,
    occurred_at: datetime,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> ExperimentEvent | None:
    """Return a `price_disagreement` event when |yf - stooq| / yf > threshold."""
    if yfinance.ticker != stooq.ticker:
        raise ValueError(
            f"price reconciliation requires matching tickers; "
            f"got {yfinance.ticker} vs {stooq.ticker}"
        )
    if yfinance.as_of.date() != stooq.as_of.date():
        raise ValueError(
            f"price reconciliation requires same trading day; "
            f"got yfinance={yfinance.as_of.date()} vs stooq={stooq.as_of.date()}"
        )
    if yfinance.close_price <= 0:
        raise ValueError("yfinance close_price must be positive for reconciliation")

    diff = abs(yfinance.close_price - stooq.close_price)
    diff_fraction = diff / yfinance.close_price
    if diff_fraction <= threshold:
        return None

    payload = {
        "ticker": yfinance.ticker,
        "as_of": yfinance.as_of.isoformat(),
        "yfinance_close": str(yfinance.close_price),
        "stooq_close": str(stooq.close_price),
        "diff_fraction": str(diff_fraction),
        "threshold": str(threshold),
    }
    return build_event(
        kind="price_disagreement",
        run_id=None,
        payload=payload,
        occurred_at=occurred_at,
        severity="warn",
    )


def reconcile_prices(
    *,
    yfinance_snapshots: Iterable[MarketPriceSnapshot],
    stooq_snapshots: Iterable[MarketPriceSnapshot],
    event_sink: Callable[[ExperimentEvent], None],
    now: datetime,
    threshold: Decimal = _DEFAULT_THRESHOLD,
) -> None:
    """Pair snapshots by ticker and emit disagreement events to the sink."""
    yf_by_ticker = {snap.ticker: snap for snap in yfinance_snapshots}
    stooq_by_ticker = {snap.ticker: snap for snap in stooq_snapshots}
    common = yf_by_ticker.keys() & stooq_by_ticker.keys()
    for ticker in sorted(common):
        event = detect_price_disagreement(
            yfinance=yf_by_ticker[ticker],
            stooq=stooq_by_ticker[ticker],
            occurred_at=now,
            threshold=threshold,
        )
        if event is not None:
            event_sink(event)


__all__ = ["detect_price_disagreement", "reconcile_prices"]
