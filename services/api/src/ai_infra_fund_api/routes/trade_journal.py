from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Callable, Protocol
from uuid import uuid4

from fastapi import APIRouter, Body, FastAPI, Query
from fastapi.responses import JSONResponse

from ai_infra_fund_core.contracts.common import TradeSide, TradeStatus, coerce_enum
from ai_infra_fund_core.contracts.portfolio import TradeEntry
from ai_infra_fund_core.runtime.config import RuntimeSettings


SettingsProvider = Callable[[], RuntimeSettings]
MANUAL_UI_SOURCE = "manual_ui"


class TradeJournalPersistenceRepository(Protocol):
    def create_trade_entry(self, trade_entry: TradeEntry) -> TradeEntry:
        ...

    def list_trade_entries(self, limit: int = 25) -> tuple[TradeEntry, ...]:
        ...


class TradeEntryValidationError(ValueError):
    pass


class PostgresTradeJournalRepository:
    def __init__(self, settings_provider: SettingsProvider) -> None:
        self._settings_provider = settings_provider

    def create_trade_entry(self, trade_entry: TradeEntry) -> TradeEntry:
        import psycopg

        from ai_infra_fund_api.repositories.trade_journal import TradeJournalRepository

        settings = self._settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            return TradeJournalRepository(connection).create_trade_entry(trade_entry)

    def list_trade_entries(self, limit: int = 25) -> tuple[TradeEntry, ...]:
        import psycopg

        from ai_infra_fund_api.repositories.trade_journal import TradeJournalRepository

        settings = self._settings_provider()
        with psycopg.connect(settings.database_url) as connection:
            return TradeJournalRepository(connection).list_trade_entries(limit=limit)


def register_trade_journal_routes(
    app: FastAPI,
    *,
    trade_journal_repository: TradeJournalPersistenceRepository | None,
    settings_provider: SettingsProvider,
) -> None:
    repository = trade_journal_repository or PostgresTradeJournalRepository(settings_provider)
    router = APIRouter()

    @router.get("/internal/trade-journal/entries")
    def list_trade_entries(limit: int = Query(default=25, ge=1, le=100)) -> JSONResponse:
        try:
            entries = repository.list_trade_entries(limit=limit)
        except Exception:
            return _error_response("trade_journal_unavailable", "trade journal entries could not be loaded", 500)

        return _data_response(
            {
                "journal_only": True,
                "total_entries": len(entries),
                "entries": [_trade_entry_payload(entry) for entry in entries],
            }
        )

    @router.post("/internal/trade-journal/entries")
    def create_trade_entry(payload: dict[str, object] = Body(...)) -> JSONResponse:
        try:
            trade_entry = prepare_trade_entry(payload)
        except TradeEntryValidationError as error:
            return _error_response("invalid_trade_entry", str(error), 422)

        try:
            saved_entry = repository.create_trade_entry(trade_entry)
        except Exception:
            return _error_response("trade_journal_persistence_failed", "trade journal entry could not be persisted", 500)

        return _data_response(_trade_entry_payload(saved_entry), status_code=201)

    app.include_router(router)


def prepare_trade_entry(payload: Mapping[str, object]) -> TradeEntry:
    errors: list[str] = []

    ticker = _required_text(payload.get("ticker"), "ticker", errors).upper()
    side = _enum_value(payload.get("side"), TradeSide, "side", errors)
    quantity = _positive_decimal(payload.get("quantity"), "quantity", errors)
    price = _optional_non_negative_decimal(payload.get("price"), "price", errors)
    fees = _optional_non_negative_decimal(payload.get("fees"), "fees", errors) or Decimal("0")
    trade_date = _required_date(payload.get("trade_date"), "trade_date", errors)
    settlement_date = _optional_date(payload.get("settlement_date"), "settlement_date", errors)
    account_label = _required_text(payload.get("account_label"), "account_label", errors)
    status = _enum_value(payload.get("status"), TradeStatus, "status", errors)
    notes = _optional_text(payload.get("notes"), "notes", errors)

    if errors:
        raise TradeEntryValidationError("; ".join(errors))

    try:
        return TradeEntry(
            trade_id=str(uuid4()),
            ticker=ticker,
            side=side,
            quantity=quantity,
            price=price,
            fees=fees,
            trade_date=trade_date,
            settlement_date=settlement_date,
            account_label=account_label,
            status=status,
            source=MANUAL_UI_SOURCE,
            notes=notes,
            created_at=datetime.now(timezone.utc),
        )
    except ValueError as error:
        raise TradeEntryValidationError(str(error)) from error


def _trade_entry_payload(trade_entry: TradeEntry) -> dict[str, object]:
    return {
        "trade_id": trade_entry.trade_id,
        "ticker": trade_entry.ticker,
        "side": trade_entry.side.value,
        "quantity": str(trade_entry.quantity),
        "price": None if trade_entry.price is None else str(trade_entry.price),
        "fees": str(trade_entry.fees),
        "trade_date": trade_entry.trade_date.isoformat(),
        "settlement_date": None if trade_entry.settlement_date is None else trade_entry.settlement_date.isoformat(),
        "account_label": trade_entry.account_label,
        "status": trade_entry.status.value,
        "source": trade_entry.source,
        "notes": trade_entry.notes,
        "created_at": trade_entry.created_at.isoformat(),
        "journal_only": True,
        "advisory_only": True,
    }


def _required_text(value: object, field_name: str, errors: list[str]) -> str:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required")
        return ""
    return value.strip()


def _optional_text(value: object, field_name: str, errors: list[str]) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        errors.append(f"{field_name} must be text")
        return None
    return value.strip() or None


def _enum_value(value: object, enum_type: type[TradeSide] | type[TradeStatus], field_name: str, errors: list[str]) -> object:
    if not isinstance(value, str):
        errors.append(f"{field_name} is required")
        return ""
    try:
        return coerce_enum(value.lower(), enum_type, field_name)
    except ValueError as error:
        errors.append(str(error))
        return ""


def _positive_decimal(value: object, field_name: str, errors: list[str]) -> Decimal:
    decimal_value = _decimal(value, field_name, errors)
    if decimal_value <= 0:
        errors.append(f"{field_name} must be positive")
    return decimal_value


def _optional_non_negative_decimal(value: object, field_name: str, errors: list[str]) -> Decimal | None:
    if value is None or value == "":
        return None
    decimal_value = _decimal(value, field_name, errors)
    if decimal_value < 0:
        errors.append(f"{field_name} must be non-negative")
    return decimal_value


def _decimal(value: object, field_name: str, errors: list[str]) -> Decimal:
    if value is None or value == "":
        errors.append(f"{field_name} is required")
        return Decimal("0")
    try:
        return Decimal(str(value))
    except InvalidOperation:
        errors.append(f"{field_name} must be decimal")
        return Decimal("0")


def _required_date(value: object, field_name: str, errors: list[str]) -> date:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{field_name} is required")
        return date(1970, 1, 1)
    return _parse_date(value, field_name, errors)


def _optional_date(value: object, field_name: str, errors: list[str]) -> date | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        errors.append(f"{field_name} must be an ISO date")
        return None
    return _parse_date(value, field_name, errors)


def _parse_date(value: str, field_name: str, errors: list[str]) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError:
        errors.append(f"{field_name} must be an ISO date")
        return date(1970, 1, 1)


def _data_response(payload: dict[str, object], status_code: int = 200) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"data": payload})


def _error_response(code: str, message: str, status_code: int) -> JSONResponse:
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
