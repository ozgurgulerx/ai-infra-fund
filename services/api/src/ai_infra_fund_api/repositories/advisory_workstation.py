from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
import json
from typing import Protocol


class Cursor(Protocol):
    description: object

    def execute(
        self, statement: str, params: tuple[object, ...] | None = None
    ) -> None: ...

    def fetchall(self) -> list[object]: ...


class Connection(Protocol):
    def cursor(self) -> object: ...


LATEST_SOURCE_SIGNALS_SQL = """
SELECT
    signal_id,
    source_type,
    signal_category,
    title,
    observed_at,
    available_at,
    tickers,
    themes,
    evidence_ids,
    derived_market_event_ids,
    confidence,
    review_status,
    payload_json
FROM analyst.source_signals
ORDER BY available_at DESC, signal_id ASC
LIMIT %s;
"""


LATEST_MARKET_EVENTS_SQL = """
SELECT
    event_id,
    event_type,
    source_signal_ids,
    evidence_ids,
    tickers,
    companies,
    themes,
    catalyst,
    ai_relevance,
    direction,
    time_horizon,
    confidence,
    occurred_at,
    available_at,
    content_hash,
    extracted_by_model_run_id,
    review_status,
    payload_json
FROM analyst.market_events
ORDER BY available_at DESC, event_id ASC
LIMIT %s;
"""


LATEST_SEGMENT_IMPACTS_SQL = """
SELECT
    segment_id,
    segment_name,
    primary_tickers,
    second_order_tickers,
    linked_event_ids,
    impact_direction,
    impact_summary,
    evidence_ids,
    payload_json
FROM analyst.segment_impacts
ORDER BY segment_id ASC
LIMIT %s;
"""


LATEST_EQUITY_ASSESSMENTS_SQL = """
SELECT
    assessment_id,
    ticker,
    company,
    linked_event_ids,
    assessment,
    watch_items,
    advisory_implication,
    risk_flags,
    invalidation,
    evidence_ids,
    payload_json
FROM analyst.equity_impact_assessments
ORDER BY ticker ASC, assessment_id ASC
LIMIT %s;
"""


LATEST_RISK_REGIME_SQL = """
SELECT
    regime_id,
    risk_type,
    status,
    linked_event_ids,
    evidence_ids,
    summary,
    portfolio_monitoring_note,
    payload_json
FROM analyst.macro_regime_snapshots
ORDER BY created_at DESC, regime_id ASC
LIMIT %s;
"""


LATEST_TRADING_ADVISORY_SQL = """
SELECT
    advisory_id,
    recommendation_artifact_id,
    ticker,
    advisory_label,
    analyst_action,
    advisory_summary,
    evidence_ids,
    model_run_ids,
    signal_bundle_id,
    target_weights_id,
    deterministic_checks,
    linked_trade_plan_id,
    payload_json
FROM analyst.trading_advisories
ORDER BY created_at DESC, advisory_id ASC
LIMIT %s;
"""


LATEST_BRIEF_SQL = """
SELECT
    brief_id,
    as_of,
    title,
    advisory_label,
    executive_summary,
    market_event_ids,
    segment_impact_ids,
    trading_advisory_ids,
    model_run_ids,
    payload_json
FROM analyst.analyst_briefs
ORDER BY as_of DESC, created_at DESC
LIMIT 1;
"""


MARKET_EVENTS_BY_IDS_SQL = LATEST_MARKET_EVENTS_SQL.replace(
    "ORDER BY available_at DESC, event_id ASC",
    "WHERE event_id = ANY(%s::text[]) "
    "ORDER BY array_position(%s::text[], event_id), event_id ASC",
)


SEGMENT_IMPACTS_BY_IDS_SQL = LATEST_SEGMENT_IMPACTS_SQL.replace(
    "ORDER BY segment_id ASC",
    "WHERE segment_id = ANY(%s::text[]) "
    "ORDER BY array_position(%s::text[], segment_id), segment_id ASC",
)


EQUITY_ASSESSMENTS_BY_EVENT_IDS_SQL = LATEST_EQUITY_ASSESSMENTS_SQL.replace(
    "ORDER BY ticker ASC, assessment_id ASC",
    "WHERE linked_event_ids && %s::text[] ORDER BY ticker ASC, assessment_id ASC",
)


RISK_REGIME_BY_EVENT_IDS_SQL = LATEST_RISK_REGIME_SQL.replace(
    "ORDER BY created_at DESC, regime_id ASC",
    "WHERE linked_event_ids && %s::text[] ORDER BY created_at DESC, regime_id ASC",
)


TRADING_ADVISORY_BY_IDS_SQL = LATEST_TRADING_ADVISORY_SQL.replace(
    "ORDER BY created_at DESC, advisory_id ASC",
    "WHERE advisory_id = ANY(%s::text[]) "
    "ORDER BY array_position(%s::text[], advisory_id), advisory_id ASC",
)


TICKER_SOURCE_SIGNALS_SQL = LATEST_SOURCE_SIGNALS_SQL.replace(
    "ORDER BY available_at DESC, signal_id ASC",
    "WHERE tickers @> ARRAY[UPPER(%s)]::text[] ORDER BY available_at DESC, signal_id ASC",
)

TICKER_MARKET_EVENTS_SQL = LATEST_MARKET_EVENTS_SQL.replace(
    "ORDER BY available_at DESC, event_id ASC",
    "WHERE tickers @> ARRAY[UPPER(%s)]::text[] ORDER BY available_at DESC, event_id ASC",
)

TICKER_EQUITY_ASSESSMENTS_SQL = LATEST_EQUITY_ASSESSMENTS_SQL.replace(
    "ORDER BY ticker ASC, assessment_id ASC",
    "WHERE UPPER(ticker) = UPPER(%s) ORDER BY ticker ASC, assessment_id ASC",
)

TICKER_VALUATION_CONTEXTS_SQL = """
SELECT
    valuation_context_id,
    ticker,
    valuation_state,
    forward_pe,
    ev_sales,
    assumptions,
    risk_flags,
    evidence_ids,
    payload_json
FROM analyst.valuation_contexts
WHERE UPPER(ticker) = UPPER(%s)
ORDER BY created_at DESC, valuation_context_id ASC
LIMIT %s;
"""

TICKER_TRADING_ADVISORY_SQL = LATEST_TRADING_ADVISORY_SQL.replace(
    "ORDER BY created_at DESC, advisory_id ASC",
    "WHERE UPPER(ticker) = UPPER(%s) ORDER BY created_at DESC, advisory_id ASC",
)


class AdvisoryWorkstationRepository:
    def __init__(self, connection: Connection) -> None:
        self._connection = connection

    def get_latest_source_signals(self, limit: int = 10) -> dict[str, object]:
        rows = self._fetch_many(LATEST_SOURCE_SIGNALS_SQL, (_limit(limit),))
        return {
            "status": _status(rows),
            "advisory_label": "advisory_only",
            "items": [_source_signal_payload(row) for row in rows],
        }

    def get_latest_market_events(self, limit: int = 10) -> dict[str, object]:
        rows = self._fetch_many(LATEST_MARKET_EVENTS_SQL, (_limit(limit),))
        return {
            "status": _status(rows),
            "advisory_label": "advisory_only",
            "items": [_market_event_payload(row) for row in rows],
        }

    def get_market_events_for_ticker(
        self, ticker: str, limit: int = 10
    ) -> dict[str, object]:
        normalized = str(ticker).upper()
        rows = self._fetch_many(
            TICKER_MARKET_EVENTS_SQL, (normalized, _limit(limit))
        )
        return {
            "status": _status(rows),
            "ticker": normalized,
            "advisory_label": "advisory_only",
            "freshness": _freshness(rows),
            "items": [_market_event_payload(row) for row in rows],
        }

    def get_latest_trading_advisory(self, limit: int = 10) -> dict[str, object]:
        rows = self._fetch_many(LATEST_TRADING_ADVISORY_SQL, (_limit(limit),))
        return {
            "status": _status(rows),
            "advisory_label": "advisory_only",
            "items": [_trading_advisory_payload(row) for row in rows],
        }

    def get_latest_analyst_brief(self) -> dict[str, object]:
        brief = self._fetch_one(LATEST_BRIEF_SQL)
        if not brief:
            return {
                "status": "empty",
                "advisory_label": "advisory_only",
                "detail": "No API-backed analyst brief has been produced.",
            }

        market_event_ids = _text_list(brief.get("market_event_ids"))
        segment_impact_ids = _text_list(brief.get("segment_impact_ids"))
        trading_advisory_ids = _text_list(brief.get("trading_advisory_ids"))
        market_events = (
            self._fetch_many(
                MARKET_EVENTS_BY_IDS_SQL,
                (market_event_ids, market_event_ids, _limit(len(market_event_ids))),
            )
            if market_event_ids
            else []
        )
        segment_impacts = (
            self._fetch_many(
                SEGMENT_IMPACTS_BY_IDS_SQL,
                (
                    segment_impact_ids,
                    segment_impact_ids,
                    _limit(len(segment_impact_ids)),
                ),
            )
            if segment_impact_ids
            else []
        )
        equity_assessments = (
            self._fetch_many(
                EQUITY_ASSESSMENTS_BY_EVENT_IDS_SQL,
                (market_event_ids, 50),
            )
            if market_event_ids
            else []
        )
        risk_regime_updates = (
            self._fetch_many(
                RISK_REGIME_BY_EVENT_IDS_SQL,
                (market_event_ids, 10),
            )
            if market_event_ids
            else []
        )
        trading_advisories = (
            self._fetch_many(
                TRADING_ADVISORY_BY_IDS_SQL,
                (
                    trading_advisory_ids,
                    trading_advisory_ids,
                    _limit(len(trading_advisory_ids)),
                ),
            )
            if trading_advisory_ids
            else []
        )

        return {
            "status": "available",
            "advisory_label": "advisory_only",
            "brief": _brief_payload(brief),
            "market_events": [
                _market_event_payload(row) for row in market_events
            ],
            "segment_impacts": [
                _segment_impact_payload(row) for row in segment_impacts
            ],
            "equity_impact_assessments": [
                _equity_assessment_payload(row) for row in equity_assessments
            ],
            "risk_regime_updates": [
                _risk_regime_payload(row) for row in risk_regime_updates
            ],
            "trading_advisories": [
                _trading_advisory_payload(row) for row in trading_advisories
            ],
        }

    def get_ticker_analyst_summary(self, ticker: str) -> dict[str, object]:
        normalized = str(ticker).upper()
        source_signals = self._fetch_many(
            TICKER_SOURCE_SIGNALS_SQL, (normalized, 10)
        )
        market_events = self._fetch_many(
            TICKER_MARKET_EVENTS_SQL, (normalized, 10)
        )
        assessments = self._fetch_many(
            TICKER_EQUITY_ASSESSMENTS_SQL, (normalized, 10)
        )
        valuation_contexts = self._fetch_many(
            TICKER_VALUATION_CONTEXTS_SQL, (normalized, 10)
        )
        advisories = self._fetch_many(
            TICKER_TRADING_ADVISORY_SQL, (normalized, 10)
        )
        sections = source_signals + market_events + assessments + valuation_contexts + advisories
        return {
            "status": _status(sections),
            "ticker": normalized,
            "advisory_label": "advisory_only",
            "source_signals": [_source_signal_payload(row) for row in source_signals],
            "market_events": [_market_event_payload(row) for row in market_events],
            "equity_impact_assessments": [
                _equity_assessment_payload(row) for row in assessments
            ],
            "valuation_contexts": [
                _valuation_context_payload(row) for row in valuation_contexts
            ],
            "trading_advisories": [
                _trading_advisory_payload(row) for row in advisories
            ],
        }

    def _fetch_one(
        self,
        statement: str,
        params: tuple[object, ...] | None = None,
    ) -> dict[str, object]:
        rows = self._fetch_many(statement, params)
        return rows[0] if rows else {}

    def _fetch_many(
        self,
        statement: str,
        params: tuple[object, ...] | None = None,
    ) -> list[dict[str, object]]:
        with self._connection.cursor() as cursor:
            cursor.execute(statement, params or ())
            rows = cursor.fetchall()
            column_names = _column_names(cursor.description)
        return [_row_to_dict(row, column_names) for row in rows]


def _source_signal_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "signal_id": row.get("signal_id"),
        "source_type": row.get("source_type"),
        "signal_category": row.get("signal_category"),
        "title": row.get("title"),
        "observed_at": _iso_or_none(row.get("observed_at")),
        "available_at": _iso_or_none(row.get("available_at")),
        "tickers": _text_list(row.get("tickers")),
        "themes": _text_list(row.get("themes")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "derived_market_event_ids": _text_list(row.get("derived_market_event_ids")),
        "confidence": row.get("confidence"),
        "review_status": row.get("review_status"),
        "payload": _json_value(row.get("payload_json")),
    }


def _market_event_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "event_id": row.get("event_id"),
        "event_type": row.get("event_type"),
        "source_signal_ids": _text_list(row.get("source_signal_ids")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "source_evidence_ids": _text_list(row.get("evidence_ids")),
        "tickers": _text_list(row.get("tickers")),
        "companies": _text_list(row.get("companies")),
        "themes": _text_list(row.get("themes")),
        "catalyst": row.get("catalyst"),
        "ai_relevance": row.get("ai_relevance"),
        "direction": row.get("direction"),
        "time_horizon": row.get("time_horizon"),
        "confidence": row.get("confidence"),
        "occurred_at": _iso_or_none(row.get("occurred_at")),
        "available_at": _iso_or_none(row.get("available_at")),
        "content_hash": row.get("content_hash"),
        "extracted_by_model_run_id": row.get("extracted_by_model_run_id"),
        "review_status": row.get("review_status"),
        "payload": _json_value(row.get("payload_json")),
    }


def _segment_impact_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "segment_id": row.get("segment_id"),
        "segment_name": row.get("segment_name"),
        "primary_tickers": _text_list(row.get("primary_tickers")),
        "second_order_tickers": _text_list(row.get("second_order_tickers")),
        "linked_event_ids": _text_list(row.get("linked_event_ids")),
        "impact_direction": row.get("impact_direction"),
        "impact_summary": row.get("impact_summary"),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "payload": _json_value(row.get("payload_json")),
    }


def _equity_assessment_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "assessment_id": row.get("assessment_id"),
        "ticker": row.get("ticker"),
        "company": row.get("company"),
        "linked_event_ids": _text_list(row.get("linked_event_ids")),
        "assessment": row.get("assessment"),
        "watch_items": _text_list(row.get("watch_items")),
        "advisory_implication": row.get("advisory_implication"),
        "risk_flags": _text_list(row.get("risk_flags")),
        "invalidation": row.get("invalidation"),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "payload": _json_value(row.get("payload_json")),
    }


def _valuation_context_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "valuation_context_id": row.get("valuation_context_id"),
        "ticker": row.get("ticker"),
        "valuation_state": row.get("valuation_state"),
        "forward_pe": row.get("forward_pe"),
        "ev_sales": row.get("ev_sales"),
        "assumptions": _text_list(row.get("assumptions")),
        "risk_flags": _text_list(row.get("risk_flags")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "payload": _json_value(row.get("payload_json")),
    }


def _risk_regime_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "regime_id": row.get("regime_id"),
        "risk_type": row.get("risk_type"),
        "status": row.get("status"),
        "linked_event_ids": _text_list(row.get("linked_event_ids")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "summary": row.get("summary"),
        "portfolio_monitoring_note": row.get("portfolio_monitoring_note"),
        "payload": _json_value(row.get("payload_json")),
    }


def _trading_advisory_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "advisory_id": row.get("advisory_id"),
        "recommendation_artifact_id": row.get("recommendation_artifact_id"),
        "ticker": row.get("ticker"),
        "advisory_label": row.get("advisory_label"),
        "analyst_action": row.get("analyst_action"),
        "advisory_summary": row.get("advisory_summary"),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "model_run_ids": _text_list(row.get("model_run_ids")),
        "signal_bundle_id": row.get("signal_bundle_id"),
        "target_weights_id": row.get("target_weights_id"),
        "deterministic_checks": _text_list(row.get("deterministic_checks")),
        "linked_trade_plan_id": row.get("linked_trade_plan_id"),
        "payload": _json_value(row.get("payload_json")),
    }


def _brief_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "brief_id": row.get("brief_id"),
        "as_of": _iso_or_none(row.get("as_of")),
        "title": row.get("title"),
        "advisory_label": row.get("advisory_label"),
        "executive_summary": row.get("executive_summary"),
        "market_event_ids": _text_list(row.get("market_event_ids")),
        "segment_impact_ids": _text_list(row.get("segment_impact_ids")),
        "trading_advisory_ids": _text_list(row.get("trading_advisory_ids")),
        "model_run_ids": _text_list(row.get("model_run_ids")),
        "payload": _json_value(row.get("payload_json")),
    }


def _status(rows: Sequence[object]) -> str:
    return "available" if rows else "empty"


def _freshness(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    available_values = [
        _iso_or_none(row.get("available_at"))
        for row in rows
        if _iso_or_none(row.get("available_at")) is not None
    ]
    return {
        "latest_available_at": max(available_values) if available_values else None,
        "item_count": len(rows),
    }


def _limit(value: int) -> int:
    return max(1, min(int(value), 50))


def _column_names(description: object) -> tuple[str, ...]:
    return tuple(_column_name(item) for item in description or ())


def _column_name(item: object) -> str:
    name = getattr(item, "name", None)
    if name is not None:
        return str(name)
    return str(item[0])  # type: ignore[index]


def _row_to_dict(row: object, column_names: tuple[str, ...]) -> dict[str, object]:
    if isinstance(row, Mapping):
        return dict(row)
    return dict(zip(column_names, row, strict=True))  # type: ignore[arg-type]


def _json_value(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        return json.loads(value)
    return value


def _text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Sequence):
        return [str(item) for item in value]
    return [str(value)]


def _iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


__all__ = ["AdvisoryWorkstationRepository"]
