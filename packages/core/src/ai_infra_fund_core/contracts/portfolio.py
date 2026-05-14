from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from .common import (
    AssetType,
    TradeSide,
    TradeStatus,
    coerce_enum,
    normalize_tuple,
    require_aware_datetime,
    require_non_empty_tuple,
    require_non_negative,
    require_positive,
    require_text,
)


@dataclass(frozen=True, slots=True)
class Position:
    position_id: str
    ticker: str
    quantity: Decimal
    cost_basis: Decimal | None
    currency: str
    account_label: str | None
    asset_type: AssetType
    opened_at: date | None
    notes: str | None
    source: str
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "position_id", require_text(self.position_id, "position_id"))
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "quantity", Decimal(str(self.quantity)))
        if self.cost_basis is not None:
            object.__setattr__(self, "cost_basis", require_non_negative(self.cost_basis, "cost_basis"))
        object.__setattr__(self, "currency", require_text(self.currency, "currency").upper())
        object.__setattr__(self, "asset_type", coerce_enum(self.asset_type, AssetType, "asset_type"))
        object.__setattr__(self, "source", require_text(self.source, "source"))
        require_aware_datetime(self.created_at, "created_at")
        require_aware_datetime(self.updated_at, "updated_at")


@dataclass(frozen=True, slots=True)
class TradeEntry:
    trade_id: str
    ticker: str
    side: TradeSide
    quantity: Decimal
    price: Decimal | None
    fees: Decimal
    trade_date: date
    settlement_date: date | None
    account_label: str | None
    status: TradeStatus
    source: str
    notes: str | None
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "trade_id", require_text(self.trade_id, "trade_id"))
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "side", coerce_enum(self.side, TradeSide, "side"))
        object.__setattr__(self, "quantity", require_positive(self.quantity, "quantity"))
        if self.price is not None:
            object.__setattr__(self, "price", require_non_negative(self.price, "price"))
        object.__setattr__(self, "fees", require_non_negative(self.fees, "fees"))
        object.__setattr__(self, "status", coerce_enum(self.status, TradeStatus, "status"))
        object.__setattr__(self, "source", require_text(self.source, "source"))
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class TradeJournal:
    journal_id: str
    entries: tuple[TradeEntry, ...]
    as_of: datetime
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "journal_id", require_text(self.journal_id, "journal_id"))
        object.__setattr__(
            self,
            "entries",
            require_non_empty_tuple(normalize_tuple(self.entries, "entries"), "entries"),
        )
        require_aware_datetime(self.as_of, "as_of")
        require_aware_datetime(self.created_at, "created_at")


@dataclass(frozen=True, slots=True)
class UniverseMember:
    universe_member_id: str
    ticker: str
    name: str | None
    theme: str
    role: str
    watchlist_status: str
    max_weight: Decimal | None
    liquidity_floor: Decimal | None
    thesis_source: str | None
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "universe_member_id", require_text(self.universe_member_id, "universe_member_id"))
        object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        object.__setattr__(self, "theme", require_text(self.theme, "theme"))
        object.__setattr__(self, "role", require_text(self.role, "role"))
        object.__setattr__(self, "watchlist_status", require_text(self.watchlist_status, "watchlist_status"))
        if self.max_weight is not None:
            object.__setattr__(self, "max_weight", require_non_negative(self.max_weight, "max_weight"))
        if self.liquidity_floor is not None:
            object.__setattr__(self, "liquidity_floor", require_non_negative(self.liquidity_floor, "liquidity_floor"))
        require_aware_datetime(self.created_at, "created_at")
        require_aware_datetime(self.updated_at, "updated_at")
