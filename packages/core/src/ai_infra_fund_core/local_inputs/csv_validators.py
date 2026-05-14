from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

from ai_infra_fund_core.contracts.common import AssetType, DataClass, TradeSide, TradeStatus, coerce_enum

from .file_validators import ensure_local_file_accepted


@dataclass(frozen=True, slots=True)
class LocalPortfolioPosition:
    ticker: str
    quantity: Decimal
    cost_basis: Decimal
    market_price: Decimal
    currency: str
    asset_type: AssetType
    account_label: str
    as_of: datetime
    available_at: datetime


@dataclass(frozen=True, slots=True)
class LocalTradeEntry:
    ticker: str
    side: TradeSide
    quantity: Decimal
    price: Decimal
    fees: Decimal
    trade_date: date
    status: TradeStatus
    account_label: str
    notes: str | None


@dataclass(frozen=True, slots=True)
class LocalUniverseMember:
    ticker: str
    name: str | None
    theme: str
    role: str
    watchlist_status: str
    max_weight: Decimal | None
    liquidity_floor: Decimal | None
    thesis_source: str | None


@dataclass(frozen=True, slots=True)
class LocalMarketSnapshot:
    ticker: str
    asset_type: AssetType
    as_of: datetime
    available_at: datetime
    source: str
    close_price: Decimal
    volume: Decimal | None


@dataclass(frozen=True, slots=True)
class LocalEvidenceFile:
    file_path: Path
    source_uri: str
    license_label: str
    data_class: DataClass
    tickers: tuple[str, ...]
    themes: tuple[str, ...]
    title: str | None
    confidence: Decimal
    horizon: str
    content: str
    local_only: bool
    quality_status: str = "accepted"


@dataclass(frozen=True, slots=True)
class LocalInputBundle:
    portfolio_positions: tuple[LocalPortfolioPosition, ...]
    trades: tuple[LocalTradeEntry, ...]
    universe: tuple[LocalUniverseMember, ...]
    market_snapshots: tuple[LocalMarketSnapshot, ...]
    evidence_files: tuple[LocalEvidenceFile, ...]


PortfolioPositionInput = LocalPortfolioPosition
MarketSnapshotInput = LocalMarketSnapshot
UniverseInput = LocalUniverseMember
EvidenceFileInput = LocalEvidenceFile


def load_portfolio_positions_csv(path: Path | str) -> tuple[LocalPortfolioPosition, ...]:
    rows = _read_rows(Path(path))
    return tuple(
        LocalPortfolioPosition(
            ticker=_required(row, "ticker").upper(),
            quantity=_decimal(row, "quantity"),
            cost_basis=_decimal(row, "cost_basis"),
            market_price=_decimal(row, "market_price"),
            currency=_required(row, "currency").upper(),
            asset_type=coerce_enum(_required(row, "asset_type").lower(), AssetType, "asset_type"),
            account_label=_required(row, "account_label"),
            as_of=_datetime(row, "as_of"),
            available_at=_datetime(row, "available_at"),
        )
        for row in rows
    )


def load_trade_journal_csv(path: Path | str) -> tuple[LocalTradeEntry, ...]:
    rows = _read_rows(Path(path))
    return tuple(
        LocalTradeEntry(
            ticker=_required(row, "ticker").upper(),
            side=coerce_enum(_required(row, "side").lower(), TradeSide, "side"),
            quantity=_decimal(row, "quantity"),
            price=_decimal(row, "price"),
            fees=_decimal(row, "fees"),
            trade_date=_date(row, "trade_date"),
            status=coerce_enum(_required(row, "status").lower(), TradeStatus, "status"),
            account_label=_required(row, "account_label"),
            notes=_optional(row, "notes"),
        )
        for row in rows
    )


def load_universe_csv(path: Path | str) -> tuple[LocalUniverseMember, ...]:
    rows = _read_rows(Path(path))
    return tuple(
        LocalUniverseMember(
            ticker=_required(row, "ticker").upper(),
            name=_optional(row, "name"),
            theme=_required(row, "theme"),
            role=_required(row, "role"),
            watchlist_status=_required(row, "watchlist_status"),
            max_weight=_optional_decimal(row, "max_weight"),
            liquidity_floor=_optional_decimal(row, "liquidity_floor"),
            thesis_source=_optional(row, "thesis_source"),
        )
        for row in rows
    )


def load_market_snapshots_csv(path: Path | str) -> tuple[LocalMarketSnapshot, ...]:
    rows = _read_rows(Path(path))
    return tuple(
        LocalMarketSnapshot(
            ticker=_required(row, "ticker").upper(),
            asset_type=coerce_enum(_required(row, "asset_type").lower(), AssetType, "asset_type"),
            as_of=_datetime(row, "as_of"),
            available_at=_datetime(row, "available_at"),
            source=_required(row, "source"),
            close_price=_decimal(row, "close_price"),
            volume=_optional_decimal(row, "volume"),
        )
        for row in rows
    )


def load_evidence_files(index_path: Path | str, root: Path | str) -> tuple[LocalEvidenceFile, ...]:
    root_path = Path(root)
    rows = _read_rows(Path(index_path))
    files: list[LocalEvidenceFile] = []
    for row in rows:
        relative_path = _required(row, "file_path")
        data_class = coerce_enum(_required(row, "data_class").lower(), DataClass, "data_class")
        content_path = ensure_local_file_accepted(root_path / relative_path)
        files.append(
            LocalEvidenceFile(
                file_path=Path(relative_path),
                source_uri=_required(row, "source_uri"),
                license_label=_required(row, "license_label"),
                data_class=data_class,
                tickers=_csv_tuple(_required(row, "tickers"), upper=True),
                themes=_csv_tuple(_required(row, "themes"), upper=False),
                title=_optional(row, "title"),
                confidence=_optional_decimal(row, "confidence") or Decimal("0.70"),
                horizon=_optional(row, "horizon") or "medium_term",
                content=content_path.read_text(encoding="utf-8"),
                local_only=data_class is DataClass.PRIVATE_RESEARCH,
            )
        )
    return tuple(files)


def load_local_input_bundle(input_dir: Path | str) -> LocalInputBundle:
    root = Path(input_dir)
    return LocalInputBundle(
        portfolio_positions=load_portfolio_positions_csv(root / "portfolio_positions.csv"),
        trades=load_trade_journal_csv(root / "trade_journal.csv"),
        universe=load_universe_csv(root / "universe.csv"),
        market_snapshots=load_market_snapshots_csv(root / "market_snapshots.csv"),
        evidence_files=load_evidence_files(root / "evidence_index.csv", root),
    )


def _read_rows(path: Path) -> tuple[dict[str, str], ...]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return tuple({str(key): str(value or "") for key, value in row.items()} for row in reader)


def _required(row: dict[str, str], field_name: str) -> str:
    value = row.get(field_name, "").strip()
    if not value:
        raise ValueError(f"{field_name} is required")
    return value


def _optional(row: dict[str, str], field_name: str) -> str | None:
    value = row.get(field_name, "").strip()
    return value or None


def _decimal(row: dict[str, str], field_name: str) -> Decimal:
    value = _required(row, field_name)
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be decimal") from exc


def _optional_decimal(row: dict[str, str], field_name: str) -> Decimal | None:
    value = _optional(row, field_name)
    if value is None:
        return None
    try:
        return Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"{field_name} must be decimal") from exc


def _datetime(row: dict[str, str], field_name: str) -> datetime:
    value = _required(row, field_name)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.tzinfo.utcoffset(parsed) is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return parsed


def _date(row: dict[str, str], field_name: str) -> date:
    return date.fromisoformat(_required(row, field_name))


def _csv_tuple(value: str, *, upper: bool) -> tuple[str, ...]:
    values = tuple(part.strip() for part in value.split(",") if part.strip())
    if upper:
        return tuple(value.upper() for value in values)
    return values
