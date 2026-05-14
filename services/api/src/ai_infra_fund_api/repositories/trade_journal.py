from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Protocol

from ai_infra_fund_core.contracts.portfolio import TradeEntry


class Cursor(Protocol):
    description: object

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchone(self) -> object | None:
        ...

    def fetchall(self) -> list[object]:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


TRADE_ENTRY_COLUMNS = """
trade_id,
ticker,
side,
quantity,
price,
fees,
trade_date,
settlement_date,
account_label,
status,
source,
notes,
created_at
"""


INSERT_TRADE_ENTRY_SQL = f"""
INSERT INTO core.trade_entries (
    {TRADE_ENTRY_COLUMNS}
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
RETURNING {TRADE_ENTRY_COLUMNS};
"""


SELECT_TRADE_ENTRIES_SQL = f"""
SELECT {TRADE_ENTRY_COLUMNS}
FROM core.trade_entries
ORDER BY created_at DESC, trade_date DESC, ticker ASC
LIMIT %s;
"""


class TradeJournalRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def create_trade_entry(self, trade_entry: TradeEntry) -> TradeEntry:
        with self._connection.cursor() as cursor:
            cursor.execute(INSERT_TRADE_ENTRY_SQL, _trade_entry_params(trade_entry))
            row = cursor.fetchone()
            column_names = _column_names(cursor.description)
        self._connection.commit()
        if row is None:
            raise RuntimeError("trade entry insert returned no row")
        return _trade_entry_from_row(row, column_names)

    def list_trade_entries(self, limit: int = 25) -> tuple[TradeEntry, ...]:
        safe_limit = max(1, min(int(limit), 100))
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_TRADE_ENTRIES_SQL, (safe_limit,))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        return tuple(_trade_entry_from_row(row, column_names) for row in rows)


def _trade_entry_params(trade_entry: TradeEntry) -> tuple[object, ...]:
    return (
        trade_entry.trade_id,
        trade_entry.ticker,
        trade_entry.side.value,
        trade_entry.quantity,
        trade_entry.price,
        trade_entry.fees,
        trade_entry.trade_date,
        trade_entry.settlement_date,
        trade_entry.account_label,
        trade_entry.status.value,
        trade_entry.source,
        trade_entry.notes,
        trade_entry.created_at,
    )


def _trade_entry_from_row(row: object, column_names: tuple[str, ...]) -> TradeEntry:
    values = _row_mapping(row, column_names)
    return TradeEntry(
        trade_id=str(values["trade_id"]),
        ticker=str(values["ticker"]),
        side=str(values["side"]),
        quantity=Decimal(str(values["quantity"])),
        price=None if values["price"] is None else Decimal(str(values["price"])),
        fees=Decimal(str(values["fees"])),
        trade_date=_date_value(values["trade_date"]),
        settlement_date=None if values["settlement_date"] is None else _date_value(values["settlement_date"]),
        account_label=None if values["account_label"] is None else str(values["account_label"]),
        status=str(values["status"]),
        source=str(values["source"]),
        notes=None if values["notes"] is None else str(values["notes"]),
        created_at=_datetime_value(values["created_at"]),
    )


def _row_mapping(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, dict):
        return row
    return dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(str(getattr(column, "name", column[0])) for column in description)  # type: ignore[index]


def _date_value(value: object) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    return date.fromisoformat(str(value))


def _datetime_value(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
