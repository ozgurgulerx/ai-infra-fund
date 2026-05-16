from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import json
from typing import Protocol


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchone(self) -> object | None: ...

    def fetchall(self) -> list[object]: ...


class Connection(Protocol):
    def cursor(self) -> object: ...

    def commit(self) -> None: ...


OUTCOME_JOURNAL_COLUMNS = """
outcome_id,
manual_journal_entry_id,
advisory_id,
ticker,
market_event_ids,
evidence_ids,
review_status,
outcome_label,
invalidation_flags,
risk_flags,
gross_pnl_amount,
net_pnl_amount,
pnl_percent,
benchmark_pnl_percent,
excess_pnl_percent,
pnl_attribution_method,
pnl_attribution_note,
reviewed_at,
available_at,
advisory_label,
payload_json,
created_at,
updated_at
"""


UPSERT_OUTCOME_JOURNAL_SQL = f"""
INSERT INTO analyst.outcome_journal_entries (
    {OUTCOME_JOURNAL_COLUMNS}
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
ON CONFLICT (outcome_id) DO UPDATE SET
    manual_journal_entry_id = EXCLUDED.manual_journal_entry_id,
    advisory_id = EXCLUDED.advisory_id,
    ticker = EXCLUDED.ticker,
    market_event_ids = EXCLUDED.market_event_ids,
    evidence_ids = EXCLUDED.evidence_ids,
    review_status = EXCLUDED.review_status,
    outcome_label = EXCLUDED.outcome_label,
    invalidation_flags = EXCLUDED.invalidation_flags,
    risk_flags = EXCLUDED.risk_flags,
    gross_pnl_amount = EXCLUDED.gross_pnl_amount,
    net_pnl_amount = EXCLUDED.net_pnl_amount,
    pnl_percent = EXCLUDED.pnl_percent,
    benchmark_pnl_percent = EXCLUDED.benchmark_pnl_percent,
    excess_pnl_percent = EXCLUDED.excess_pnl_percent,
    pnl_attribution_method = EXCLUDED.pnl_attribution_method,
    pnl_attribution_note = EXCLUDED.pnl_attribution_note,
    reviewed_at = EXCLUDED.reviewed_at,
    available_at = EXCLUDED.available_at,
    advisory_label = EXCLUDED.advisory_label,
    payload_json = EXCLUDED.payload_json,
    updated_at = EXCLUDED.updated_at
RETURNING {OUTCOME_JOURNAL_COLUMNS};
"""


SELECT_LATEST_OUTCOMES_SQL = f"""
SELECT {OUTCOME_JOURNAL_COLUMNS}
FROM analyst.outcome_journal_entries
ORDER BY available_at DESC, reviewed_at DESC, outcome_id ASC
LIMIT %s;
"""


@dataclass(frozen=True, slots=True)
class OutcomeJournalEntry:
    outcome_id: str
    manual_journal_entry_id: str
    advisory_id: str
    ticker: str
    market_event_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    review_status: str
    outcome_label: str
    invalidation_flags: tuple[str, ...]
    risk_flags: tuple[str, ...]
    gross_pnl_amount: Decimal | None
    net_pnl_amount: Decimal | None
    pnl_percent: Decimal | None
    benchmark_pnl_percent: Decimal | None
    excess_pnl_percent: Decimal | None
    pnl_attribution_method: str
    pnl_attribution_note: str | None
    reviewed_at: datetime
    available_at: datetime
    advisory_label: str
    payload: Mapping[str, object]
    created_at: datetime
    updated_at: datetime


class OutcomeJournalRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def upsert_outcome(self, entry: OutcomeJournalEntry) -> OutcomeJournalEntry:
        with self._connection.cursor() as cursor:
            cursor.execute(UPSERT_OUTCOME_JOURNAL_SQL, _entry_params(entry))
            row = cursor.fetchone()
            column_names = _column_names(cursor.description)
        self._connection.commit()
        if row is None:
            raise RuntimeError("outcome journal upsert returned no row")
        return _entry_from_row(row, column_names)

    def get_latest_outcomes(self, limit: int = 25) -> dict[str, object]:
        safe_limit = max(1, min(int(limit), 100))
        with self._connection.cursor() as cursor:
            cursor.execute(SELECT_LATEST_OUTCOMES_SQL, (safe_limit,))
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        entries = [_entry_from_row(row, column_names) for row in rows]
        return {
            "status": "available" if entries else "empty",
            "advisory_label": "advisory_only",
            "total_entries": len(entries),
            "items": [_entry_payload(entry) for entry in entries],
        }


def _entry_params(entry: OutcomeJournalEntry) -> tuple[object, ...]:
    return (
        entry.outcome_id,
        entry.manual_journal_entry_id,
        entry.advisory_id,
        entry.ticker,
        list(entry.market_event_ids),
        list(entry.evidence_ids),
        entry.review_status,
        entry.outcome_label,
        list(entry.invalidation_flags),
        list(entry.risk_flags),
        entry.gross_pnl_amount,
        entry.net_pnl_amount,
        entry.pnl_percent,
        entry.benchmark_pnl_percent,
        entry.excess_pnl_percent,
        entry.pnl_attribution_method,
        entry.pnl_attribution_note,
        entry.reviewed_at,
        entry.available_at,
        entry.advisory_label,
        _json_dump(entry.payload),
        entry.created_at,
        entry.updated_at,
    )


def _entry_from_row(row: object, column_names: tuple[str, ...]) -> OutcomeJournalEntry:
    values = _row_mapping(row, column_names)
    return OutcomeJournalEntry(
        outcome_id=str(values["outcome_id"]),
        manual_journal_entry_id=str(values["manual_journal_entry_id"]),
        advisory_id=str(values["advisory_id"]),
        ticker=str(values["ticker"]),
        market_event_ids=tuple(_text_list(values["market_event_ids"])),
        evidence_ids=tuple(_text_list(values["evidence_ids"])),
        review_status=str(values["review_status"]),
        outcome_label=str(values["outcome_label"]),
        invalidation_flags=tuple(_text_list(values["invalidation_flags"])),
        risk_flags=tuple(_text_list(values["risk_flags"])),
        gross_pnl_amount=_decimal_or_none(values["gross_pnl_amount"]),
        net_pnl_amount=_decimal_or_none(values["net_pnl_amount"]),
        pnl_percent=_decimal_or_none(values["pnl_percent"]),
        benchmark_pnl_percent=_decimal_or_none(values["benchmark_pnl_percent"]),
        excess_pnl_percent=_decimal_or_none(values["excess_pnl_percent"]),
        pnl_attribution_method=str(values["pnl_attribution_method"]),
        pnl_attribution_note=(
            None
            if values["pnl_attribution_note"] is None
            else str(values["pnl_attribution_note"])
        ),
        reviewed_at=_datetime_value(values["reviewed_at"]),
        available_at=_datetime_value(values["available_at"]),
        advisory_label=str(values["advisory_label"]),
        payload=_json_value(values["payload_json"]),
        created_at=_datetime_value(values["created_at"]),
        updated_at=_datetime_value(values["updated_at"]),
    )


def _entry_payload(entry: OutcomeJournalEntry) -> dict[str, object]:
    return {
        "outcome_id": entry.outcome_id,
        "manual_journal_entry_id": entry.manual_journal_entry_id,
        "advisory_id": entry.advisory_id,
        "ticker": entry.ticker,
        "market_event_ids": list(entry.market_event_ids),
        "evidence_ids": list(entry.evidence_ids),
        "review_status": entry.review_status,
        "outcome_label": entry.outcome_label,
        "invalidation_flags": list(entry.invalidation_flags),
        "risk_flags": list(entry.risk_flags),
        "gross_pnl_amount": _decimal_text(entry.gross_pnl_amount),
        "net_pnl_amount": _decimal_text(entry.net_pnl_amount),
        "pnl_percent": _decimal_text(entry.pnl_percent),
        "benchmark_pnl_percent": _decimal_text(entry.benchmark_pnl_percent),
        "excess_pnl_percent": _decimal_text(entry.excess_pnl_percent),
        "pnl_attribution_method": entry.pnl_attribution_method,
        "pnl_attribution_note": entry.pnl_attribution_note,
        "reviewed_at": entry.reviewed_at.isoformat(),
        "available_at": entry.available_at.isoformat(),
        "advisory_label": entry.advisory_label,
        "payload": dict(entry.payload),
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def _row_mapping(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(str(getattr(column, "name", column[0])) for column in description)  # type: ignore[index]


def _decimal_or_none(value: object) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _decimal_text(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _datetime_value(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def _json_dump(value: Mapping[str, object]) -> str:
    return json.dumps(dict(value), sort_keys=True, separators=(",", ":"), default=str)


def _json_value(value: object) -> Mapping[str, object]:
    if value is None:
        return {}
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, Mapping) else {}
    if isinstance(value, Mapping):
        return value
    return {}


def _text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


__all__ = ["OutcomeJournalEntry", "OutcomeJournalRepository"]
