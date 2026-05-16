from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Mapping, Sequence

from ai_infra_fund_core.contracts.common import (
    DataClass,
    coerce_enum,
    require_aware_datetime,
    require_text,
    stable_hash_payload,
)


class AnalystContextScope(str, Enum):
    DAILY_BRIEF = "daily_brief"
    TICKER = "ticker"


COLLECTIONS = (
    "source_signals",
    "evidence_items",
    "market_events",
    "segment_impacts",
    "equity_impact_assessments",
    "valuation_contexts",
    "risk_regime_updates",
    "portfolio_exposures",
    "prior_advisories",
    "outcome_journal_entries",
)

DEFAULT_DATA_CLASS_BY_COLLECTION = {
    "source_signals": DataClass.PUBLIC_EVIDENCE,
    "evidence_items": DataClass.PUBLIC_EVIDENCE,
    "market_events": DataClass.DERIVED_ANALYTICS,
    "segment_impacts": DataClass.DERIVED_ANALYTICS,
    "equity_impact_assessments": DataClass.DERIVED_ANALYTICS,
    "valuation_contexts": DataClass.DERIVED_ANALYTICS,
    "risk_regime_updates": DataClass.DERIVED_ANALYTICS,
    "portfolio_exposures": DataClass.USER_PORTFOLIO,
    "prior_advisories": DataClass.DERIVED_ANALYTICS,
    "outcome_journal_entries": DataClass.USER_PORTFOLIO,
}

EVIDENCE_ID_FIELDS = (
    "evidence_id",
    "evidence_ids",
    "source_evidence_ids",
    "evidence_available_ids",
)

OBJECT_ID_FIELDS = (
    "signal_id",
    "evidence_id",
    "event_id",
    "segment_impact_id",
    "impact_id",
    "assessment_id",
    "valuation_context_id",
    "regime_id",
    "snapshot_id",
    "advisory_id",
    "outcome_entry_id",
)

TICKER_FIELDS = (
    "ticker",
    "tickers",
    "affected_tickers",
    "primary_tickers",
    "first_order_tickers",
    "second_order_tickers",
    "ticker_or_portfolio",
)


@dataclass(frozen=True, slots=True)
class AnalystContextBundle:
    bundle_id: str
    scope: AnalystContextScope
    as_of: datetime
    ticker: str | None
    rows: dict[str, tuple[dict[str, Any], ...]]
    evidence_ids: tuple[str, ...]
    object_ids: tuple[str, ...]
    data_classes: tuple[DataClass, ...]
    content_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "bundle_id", require_text(self.bundle_id, "bundle_id"))
        object.__setattr__(self, "scope", coerce_enum(self.scope, AnalystContextScope, "scope"))
        require_aware_datetime(self.as_of, "as_of")
        if self.ticker is not None:
            object.__setattr__(self, "ticker", require_text(self.ticker, "ticker").upper())
        if not self.evidence_ids:
            raise ValueError("AnalystContextBundle requires evidence_ids")
        if not self.object_ids:
            raise ValueError("AnalystContextBundle requires object_ids")
        if not self.data_classes:
            raise ValueError("AnalystContextBundle requires data_classes")


def build_daily_analyst_context_bundle(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    as_of: datetime,
) -> AnalystContextBundle:
    normalized = _normalize_rows(rows)
    return _build_bundle(
        scope=AnalystContextScope.DAILY_BRIEF,
        as_of=as_of,
        ticker=None,
        rows=normalized,
    )


def build_ticker_analyst_context_bundle(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    ticker: str,
    as_of: datetime,
) -> AnalystContextBundle:
    ticker_text = require_text(ticker, "ticker").upper()
    normalized = _normalize_rows(rows)
    filtered: dict[str, tuple[dict[str, Any], ...]] = {}
    for collection, collection_rows in normalized.items():
        if collection == "evidence_items":
            continue
        filtered[collection] = tuple(
            row for row in collection_rows if _row_matches_ticker(row, ticker_text)
        )

    linked_evidence_ids = _collect_evidence_ids(filtered)
    filtered["evidence_items"] = tuple(
        row
        for row in normalized["evidence_items"]
        if str(row.get("evidence_id") or "") in linked_evidence_ids
    )
    return _build_bundle(
        scope=AnalystContextScope.TICKER,
        as_of=as_of,
        ticker=ticker_text,
        rows=filtered,
    )


def _build_bundle(
    *,
    scope: AnalystContextScope,
    as_of: datetime,
    ticker: str | None,
    rows: dict[str, tuple[dict[str, Any], ...]],
) -> AnalystContextBundle:
    checked_as_of = require_aware_datetime(as_of, "as_of")
    evidence_ids = _collect_evidence_ids(rows)
    object_ids = _collect_object_ids(rows)
    data_classes = _collect_data_classes(rows)
    content_hash = stable_hash_payload(
        {
            "scope": scope.value,
            "as_of": checked_as_of,
            "ticker": ticker,
            "rows": rows,
            "evidence_ids": evidence_ids,
            "data_classes": data_classes,
        }
    )
    bundle_id = f"analyst-context-{scope.value}-{content_hash[:16]}"
    return AnalystContextBundle(
        bundle_id=bundle_id,
        scope=scope,
        as_of=checked_as_of,
        ticker=ticker,
        rows=rows,
        evidence_ids=evidence_ids,
        object_ids=object_ids,
        data_classes=data_classes,
        content_hash=content_hash,
    )


def _normalize_rows(
    rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, tuple[dict[str, Any], ...]]:
    normalized: dict[str, tuple[dict[str, Any], ...]] = {}
    for collection in COLLECTIONS:
        raw_rows = rows.get(collection, ())
        normalized[collection] = tuple(dict(row) for row in raw_rows)
    return normalized


def _collect_evidence_ids(rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[str, ...]:
    evidence_ids: list[str] = []
    for collection_rows in rows.values():
        for row in collection_rows:
            for field_name in EVIDENCE_ID_FIELDS:
                evidence_ids.extend(_text_values(row.get(field_name)))
    return _unique_texts(evidence_ids)


def _collect_object_ids(rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[str, ...]:
    object_ids: list[str] = []
    for collection_rows in rows.values():
        for row in collection_rows:
            for field_name in OBJECT_ID_FIELDS:
                object_ids.extend(_text_values(row.get(field_name)))
    return _unique_texts(object_ids)


def _collect_data_classes(rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> tuple[DataClass, ...]:
    data_classes: list[DataClass] = []
    for collection, collection_rows in rows.items():
        default = DEFAULT_DATA_CLASS_BY_COLLECTION[collection]
        for row in collection_rows:
            raw_data_class = row.get("data_class") or default
            data_classes.append(coerce_enum(raw_data_class, DataClass, "data_class"))
    return tuple(dict.fromkeys(data_classes))


def _row_matches_ticker(row: Mapping[str, Any], ticker: str) -> bool:
    for field_name in TICKER_FIELDS:
        values = tuple(value.upper() for value in _text_values(row.get(field_name)))
        if ticker in values:
            return True
    for position in _sequence(row.get("positions")):
        if isinstance(position, Mapping) and str(position.get("ticker") or "").upper() == ticker:
            return True
    return False


def _text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, Mapping):
        return []
    values: list[str] = []
    for item in _sequence(value):
        text = str(item).strip()
        if text:
            values.append(text)
    return values


def _sequence(value: Any) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def _unique_texts(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in values if value))
