from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
import hashlib
import json
from typing import Any, Iterable, TypeVar


class DataClass(str, Enum):
    PUBLIC_MARKET_DATA = "public_market_data"
    PUBLIC_EVIDENCE = "public_evidence"
    USER_PORTFOLIO = "user_portfolio"
    PRIVATE_RESEARCH = "private_research"
    RUN_AUDIT = "run_audit"
    DERIVED_ANALYTICS = "derived_analytics"
    SECRETS = "secrets"


class AssetType(str, Enum):
    EQUITY = "equity"
    ETF = "etf"
    CASH = "cash"
    FUTURE = "future"
    OPTION = "option"
    CRYPTO = "crypto"
    OTHER = "other"


class TradeSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, Enum):
    INTENDED = "intended"
    PAPER = "paper"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    IGNORED = "ignored"


class RecommendationAction(str, Enum):
    CORE_BUY = "core_buy"
    ACCUMULATE = "accumulate"
    HOLD = "hold"
    WATCH = "watch"
    TRIM = "trim"
    AVOID = "avoid"
    EXIT_CANDIDATE = "exit_candidate"


class AdvisoryLabel(str, Enum):
    ADVISORY_ONLY = "advisory_only"


class ModelRunStatus(str, Enum):
    SUCCESS = "success"
    RETRY = "retry"
    FAILURE = "failure"
    DENIED = "denied"


class IncidentSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DataQualityStatus(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"
    STALE = "stale"
    QUARANTINED = "quarantined"


EnumT = TypeVar("EnumT", bound=Enum)


def coerce_enum(value: EnumT | str, enum_type: type[EnumT], field_name: str) -> EnumT:
    try:
        return value if isinstance(value, enum_type) else enum_type(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be one of {[item.value for item in enum_type]}") from exc


def normalize_tuple(values: Iterable[Any] | None, field_name: str) -> tuple[Any, ...]:
    if values is None:
        return ()
    if isinstance(values, str):
        raise ValueError(f"{field_name} must be an iterable, not a string")
    return tuple(values)


def require_text(value: str | None, field_name: str) -> str:
    if value is None or not str(value).strip():
        raise ValueError(f"{field_name} is required")
    return str(value)


def require_content_hash(value: str | None, field_name: str = "content_hash") -> str:
    return require_text(value, field_name)


def require_non_empty_tuple(values: tuple[Any, ...], field_name: str) -> tuple[Any, ...]:
    if not values:
        raise ValueError(f"{field_name} must not be empty")
    return values


def require_aware_datetime(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
        raise ValueError(f"{field_name} must be timezone-aware")
    return value


def require_decimal_range(value: Decimal, field_name: str, low: Decimal, high: Decimal) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < low or decimal_value > high:
        raise ValueError(f"{field_name} must be between {low} and {high}")
    return decimal_value


def require_non_negative(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value < Decimal("0"):
        raise ValueError(f"{field_name} must be non-negative")
    return decimal_value


def require_positive(value: Decimal, field_name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value <= Decimal("0"):
        raise ValueError(f"{field_name} must be positive")
    return decimal_value


def canonicalize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): canonicalize(value[key]) for key in sorted(value)}
    if isinstance(value, (list, tuple)):
        return [canonicalize(item) for item in value]
    return value


def stable_hash_payload(payload: dict[str, Any]) -> str:
    encoded = json.dumps(canonicalize(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
