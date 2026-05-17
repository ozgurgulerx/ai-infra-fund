from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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
    severity,
    confidence,
    linked_event_ids,
    affected_segments,
    affected_tickers,
    evidence_ids,
    summary,
    portfolio_monitoring_note,
    relief_condition,
    invalidation_condition,
    as_of,
    available_at,
    payload_json
FROM analyst.risk_regime_updates
ORDER BY available_at DESC, regime_id ASC
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
    "ORDER BY available_at DESC, regime_id ASC",
    "WHERE linked_event_ids && %s::text[] ORDER BY available_at DESC, regime_id ASC",
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

TICKER_SEGMENT_IMPACTS_SQL = LATEST_SEGMENT_IMPACTS_SQL.replace(
    "ORDER BY segment_id ASC",
    "WHERE primary_tickers @> ARRAY[UPPER(%s)]::text[] "
    "OR second_order_tickers @> ARRAY[UPPER(%s)]::text[] "
    "ORDER BY segment_id ASC",
)

TICKER_RISK_REGIME_SQL = LATEST_RISK_REGIME_SQL.replace(
    "ORDER BY available_at DESC, regime_id ASC",
    "WHERE affected_tickers @> ARRAY[UPPER(%s)]::text[] "
    "OR linked_event_ids && %s::text[] "
    "ORDER BY available_at DESC, regime_id ASC",
)

TICKER_TRADE_PLAN_SQL = """
SELECT
    trade_plan_id,
    ticker,
    company,
    status,
    advisory_action,
    linked_event_ids,
    linked_signal_bundle_id,
    linked_recommendation_artifact_id,
    entry_exit_levels_id,
    price_target_scenario_id,
    target_weights_id,
    deterministic_check_ids,
    readiness,
    blocking_reasons,
    manual_journal_only,
    evidence_ids,
    linked_advisory_id,
    last_reviewed_at,
    payload_json
FROM analyst.trade_plans
WHERE UPPER(ticker) = UPPER(%s)
ORDER BY last_reviewed_at DESC, trade_plan_id ASC
LIMIT %s;
"""

TICKER_LLM_ANALYST_NOTES_SQL = """
SELECT
    note_id,
    model_run_id,
    scope,
    allowed_role,
    reviewed_object_ids,
    evidence_ids,
    note,
    deterministic_fields_not_modified,
    created_at,
    review_status,
    payload_json
FROM analyst.llm_analyst_notes
WHERE reviewed_object_ids && %s::text[] OR evidence_ids && %s::text[]
ORDER BY created_at DESC, note_id ASC
LIMIT %s;
"""

LATEST_PORTFOLIO_EXPOSURE_SQL = """
SELECT
    snapshot_id,
    as_of,
    currency,
    source,
    advisory_label,
    total_market_value,
    cash_placeholder,
    gross_equity_exposure,
    position_count,
    positions_json,
    correlation_exposure_ids,
    pnl_summary_id,
    target_weights_id,
    concentration_flags,
    stale_price_flags,
    payload_json
FROM analyst.portfolio_exposure_snapshots
ORDER BY as_of DESC, created_at DESC
LIMIT %s;
"""


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

    def get_latest_segment_map(self) -> dict[str, object]:
        segment_impacts = self._fetch_many(LATEST_SEGMENT_IMPACTS_SQL, (50,))
        linked_event_ids = _unique_texts(
            event_id
            for segment in segment_impacts
            for event_id in _text_list(segment.get("linked_event_ids"))
        )
        market_events = (
            self._fetch_many(
                MARKET_EVENTS_BY_IDS_SQL,
                (linked_event_ids, linked_event_ids, _limit(len(linked_event_ids))),
            )
            if linked_event_ids
            else []
        )
        risk_regime_updates = (
            self._fetch_many(RISK_REGIME_BY_EVENT_IDS_SQL, (linked_event_ids, 20))
            if linked_event_ids
            else []
        )
        return {
            "status": _status(segment_impacts),
            "advisory_label": "advisory_only",
            "segment_impacts": [
                _segment_impact_payload(row) for row in segment_impacts
            ],
            "market_events": [
                _market_event_payload(row) for row in market_events
            ],
            "risk_regime_updates": [
                _risk_regime_payload(row) for row in risk_regime_updates
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

    def get_ticker_workbench(self, ticker: str) -> dict[str, object]:
        normalized = str(ticker).upper()
        source_signals = self._fetch_many(
            TICKER_SOURCE_SIGNALS_SQL, (normalized, 10)
        )
        market_events = self._fetch_many(
            TICKER_MARKET_EVENTS_SQL, (normalized, 10)
        )
        event_ids = _unique_texts(
            event_id for row in market_events for event_id in (row.get("event_id"),)
        )
        segment_impacts = self._fetch_many(
            TICKER_SEGMENT_IMPACTS_SQL, (normalized, normalized, 10)
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
        trade_plans = self._fetch_many(TICKER_TRADE_PLAN_SQL, (normalized, 10))
        risk_regime_updates = self._fetch_many(
            TICKER_RISK_REGIME_SQL, (normalized, event_ids, 10)
        )
        reviewed_object_ids = _unique_texts(
            item_id
            for collection in (assessments, advisories, trade_plans)
            for row in collection
            for item_id in (
                row.get("assessment_id"),
                row.get("advisory_id"),
                row.get("trade_plan_id"),
            )
        )
        evidence_ids = _unique_texts(
            evidence_id
            for collection in (market_events, assessments, advisories, trade_plans)
            for row in collection
            for evidence_id in _text_list(row.get("evidence_ids"))
        )
        llm_notes = self._fetch_many(
            TICKER_LLM_ANALYST_NOTES_SQL,
            (reviewed_object_ids, evidence_ids, 10),
        )
        source_signal_payloads = [
            _source_signal_payload(row) for row in source_signals
        ]
        market_event_payloads = [_market_event_payload(row) for row in market_events]
        segment_impact_payloads = [
            _segment_impact_payload(row) for row in segment_impacts
        ]
        assessment_payloads = [
            _equity_assessment_payload(row) for row in assessments
        ]
        valuation_payloads = [
            _valuation_context_payload(row) for row in valuation_contexts
        ]
        advisory_payloads = [_trading_advisory_payload(row) for row in advisories]
        trade_plan_payloads = [_trade_plan_payload(row) for row in trade_plans]
        risk_payloads = [_risk_regime_payload(row) for row in risk_regime_updates]
        llm_note_payloads = [_llm_note_payload(row) for row in llm_notes]
        sections = (
            source_signals
            + market_events
            + segment_impacts
            + assessments
            + valuation_contexts
            + advisories
            + trade_plans
            + risk_regime_updates
            + llm_notes
        )
        return {
            "status": _status(sections),
            "ticker": normalized,
            "advisory_label": "advisory_only",
            "source_signals": source_signal_payloads,
            "market_events": market_event_payloads,
            "segment_impacts": segment_impact_payloads,
            "equity_impact_assessments": assessment_payloads,
            "valuation_contexts": valuation_payloads,
            "trading_advisories": advisory_payloads,
            "trade_plans": trade_plan_payloads,
            "risk_regime_updates": risk_payloads,
            "llm_analyst_notes": llm_note_payloads,
            "theme_groups": _ticker_theme_groups(
                normalized,
                source_signal_payloads,
                market_event_payloads,
                segment_impact_payloads,
                assessment_payloads,
                valuation_payloads,
                advisory_payloads,
                trade_plan_payloads,
                risk_payloads,
                llm_note_payloads,
            ),
        }

    def get_latest_portfolio_exposure(self) -> dict[str, object]:
        row = self._fetch_one(LATEST_PORTFOLIO_EXPOSURE_SQL, (1,))
        return {
            "status": "available" if row else "empty",
            "advisory_label": "advisory_only",
            "snapshot": _portfolio_exposure_payload(row) if row else None,
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
        "severity": row.get("severity"),
        "confidence": row.get("confidence"),
        "linked_event_ids": _text_list(row.get("linked_event_ids")),
        "affected_segments": _text_list(row.get("affected_segments")),
        "affected_tickers": _text_list(row.get("affected_tickers")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "summary": row.get("summary"),
        "portfolio_monitoring_note": row.get("portfolio_monitoring_note"),
        "relief_condition": row.get("relief_condition"),
        "invalidation_condition": row.get("invalidation_condition"),
        "as_of": _iso_or_none(row.get("as_of")),
        "available_at": _iso_or_none(row.get("available_at")),
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


def _trade_plan_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "trade_plan_id": row.get("trade_plan_id"),
        "ticker": row.get("ticker"),
        "company": row.get("company"),
        "status": row.get("status"),
        "advisory_action": row.get("advisory_action"),
        "linked_event_ids": _text_list(row.get("linked_event_ids")),
        "linked_signal_bundle_id": row.get("linked_signal_bundle_id"),
        "linked_recommendation_artifact_id": row.get("linked_recommendation_artifact_id"),
        "entry_exit_levels_id": row.get("entry_exit_levels_id"),
        "price_target_scenario_id": row.get("price_target_scenario_id"),
        "target_weights_id": row.get("target_weights_id"),
        "deterministic_check_ids": _text_list(row.get("deterministic_check_ids")),
        "readiness": row.get("readiness"),
        "blocking_reasons": _text_list(row.get("blocking_reasons")),
        "manual_journal_only": _bool(row.get("manual_journal_only")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "linked_advisory_id": row.get("linked_advisory_id"),
        "last_reviewed_at": _iso_or_none(row.get("last_reviewed_at")),
        "payload": _json_value(row.get("payload_json")),
    }


def _portfolio_exposure_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "snapshot_id": row.get("snapshot_id"),
        "as_of": _iso_or_none(row.get("as_of")),
        "currency": row.get("currency"),
        "source": row.get("source"),
        "advisory_label": row.get("advisory_label"),
        "total_market_value": row.get("total_market_value"),
        "cash_placeholder": row.get("cash_placeholder"),
        "gross_equity_exposure": row.get("gross_equity_exposure"),
        "position_count": row.get("position_count"),
        "positions": _json_value(row.get("positions_json")) or [],
        "correlation_exposure_ids": _text_list(row.get("correlation_exposure_ids")),
        "pnl_summary_id": row.get("pnl_summary_id"),
        "target_weights_id": row.get("target_weights_id"),
        "concentration_flags": _text_list(row.get("concentration_flags")),
        "stale_price_flags": _text_list(row.get("stale_price_flags")),
        "payload": _json_value(row.get("payload_json")),
    }


def _llm_note_payload(row: Mapping[str, object]) -> dict[str, object]:
    return {
        "note_id": row.get("note_id"),
        "model_run_id": row.get("model_run_id"),
        "scope": row.get("scope"),
        "allowed_role": row.get("allowed_role"),
        "reviewed_object_ids": _text_list(row.get("reviewed_object_ids")),
        "evidence_ids": _text_list(row.get("evidence_ids")),
        "note": row.get("note"),
        "deterministic_fields_not_modified": _text_list(
            row.get("deterministic_fields_not_modified")
        ),
        "created_at": _iso_or_none(row.get("created_at")),
        "review_status": row.get("review_status"),
        "payload": _json_value(row.get("payload_json")),
    }


def _ticker_theme_groups(
    ticker: str,
    source_signals: Sequence[Mapping[str, object]],
    market_events: Sequence[Mapping[str, object]],
    segment_impacts: Sequence[Mapping[str, object]],
    assessments: Sequence[Mapping[str, object]],
    valuation_contexts: Sequence[Mapping[str, object]],
    advisories: Sequence[Mapping[str, object]],
    trade_plans: Sequence[Mapping[str, object]],
    risk_regime_updates: Sequence[Mapping[str, object]],
    llm_notes: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    theme_labels = _theme_labels(
        source_signals=source_signals,
        market_events=market_events,
        segment_impacts=segment_impacts,
        impact_assessments=assessments,
        risk_regime_updates=risk_regime_updates,
    )
    if not theme_labels:
        evidence_ids = _evidence_union(
            source_signals,
            market_events,
            assessments,
            valuation_contexts,
            advisories,
            trade_plans,
            risk_regime_updates,
            llm_notes,
        )
        if not evidence_ids:
            return []
        theme_labels = ["Ticker thesis"]

    return [
        _ticker_theme_group(
            ticker,
            theme_label,
            source_signals,
            market_events,
            segment_impacts,
            assessments,
            valuation_contexts,
            advisories,
            trade_plans,
            risk_regime_updates,
            llm_notes,
        )
        for theme_label in theme_labels
    ]


def _ticker_theme_group(
    ticker: str,
    theme_label: str,
    source_signals: Sequence[Mapping[str, object]],
    market_events: Sequence[Mapping[str, object]],
    segment_impacts: Sequence[Mapping[str, object]],
    assessments: Sequence[Mapping[str, object]],
    valuation_contexts: Sequence[Mapping[str, object]],
    advisories: Sequence[Mapping[str, object]],
    trade_plans: Sequence[Mapping[str, object]],
    risk_regime_updates: Sequence[Mapping[str, object]],
    llm_notes: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    group_source_signals = [
        row for row in source_signals if _has_theme(row, theme_label)
    ] or list(source_signals[:3])
    group_market_events = [
        row for row in market_events if _has_theme(row, theme_label)
    ] or list(market_events[:5])
    event_ids = _unique_texts(row.get("event_id") for row in group_market_events)
    group_segment_impacts = [
        row
        for row in segment_impacts
        if _same_theme(row.get("segment_name"), theme_label)
        or _overlaps(_text_list(row.get("linked_event_ids")), event_ids)
    ] or list(segment_impacts[:3])
    group_assessments = [
        row
        for row in assessments
        if str(row.get("ticker") or "").upper() == ticker
        or _overlaps(_text_list(row.get("linked_event_ids")), event_ids)
    ] or list(assessments[:2])
    group_risk_updates = [
        row
        for row in risk_regime_updates
        if _has_theme(row, theme_label)
        or _overlaps(_text_list(row.get("linked_event_ids")), event_ids)
        or ticker in _text_list(row.get("affected_tickers"))
    ]
    evidence_ids = _unique_texts(
        evidence_id
        for collection in (
            group_source_signals,
            group_market_events,
            group_segment_impacts,
            group_assessments,
            valuation_contexts,
            advisories,
            trade_plans,
            group_risk_updates,
            llm_notes,
        )
        for row in collection
        for evidence_id in _text_list(row.get("evidence_ids"))
    )
    stance = _advisory_stance(
        trading_advisories=advisories,
        trade_plans=trade_plans,
        evidence_ids=evidence_ids,
        market_events=group_market_events,
    )
    source_signal_items = [
        _with_relevance(
            item,
            level="direct",
            reason=f"Source signal is linked to {theme_label}.",
        )
        for item in group_source_signals
    ]
    market_event_items = [
        _with_relevance(
            item,
            level="direct",
            reason=f"MarketEvent is linked to {theme_label}.",
        )
        for item in group_market_events
    ]
    assessment_items = [
        _with_relevance(
            item,
            level="direct",
            reason=f"Assessment is linked to {ticker} and {theme_label}.",
        )
        for item in group_assessments
    ]
    llm_note_items = [
        _with_relevance(
            item,
            level="supporting",
            reason="LLM note reviews linked evidence or analyst objects.",
        )
        for item in llm_notes
    ]
    trade_plan_note_items = [
        note for plan in trade_plans if (note := _trade_plan_note(plan))
    ]

    return {
        "theme_id": _theme_id(theme_label),
        "theme_label": theme_label,
        "ticker": ticker,
        "advisory_label": "advisory_only",
        "why_now": _why_now(group_market_events, advisories, group_assessments),
        "what_changed": _what_changed(group_source_signals, group_market_events),
        "advisory_stance": stance,
        "internal_rating": stance,
        "source_signals": source_signal_items,
        "market_events": market_event_items,
        "impact_assessments": assessment_items,
        "llm_notes": llm_note_items,
        "journal_notes": [],
        "trade_plan_notes": trade_plan_note_items,
        "news": {
            "source_signals": source_signal_items,
            "market_events": market_event_items,
        },
        "notes": {
            "llm_analyst_notes": llm_note_items,
            "trade_plan_notes": trade_plan_note_items,
        },
        "related_tickers": _related_tickers(
            ticker=ticker,
            theme_label=theme_label,
            segment_impacts=group_segment_impacts,
            market_events=group_market_events,
            evidence_ids=evidence_ids,
        ),
        "risk_flags": _risk_flags(
            group_assessments,
            valuation_contexts,
            group_risk_updates,
            trade_plans,
        ),
        "invalidation": _invalidation(group_assessments, group_risk_updates),
        "next_watch_items": _next_watch_items(
            group_assessments,
            group_risk_updates,
            trade_plans,
            group_market_events,
        ),
        "latest_available_at": _latest_available_at(
            group_source_signals,
            group_market_events,
            trade_plans,
            group_risk_updates,
            llm_notes,
        ),
        "evidence_ids": evidence_ids,
    }


def _theme_labels(
    *,
    source_signals: Sequence[Mapping[str, object]],
    market_events: Sequence[Mapping[str, object]],
    segment_impacts: Sequence[Mapping[str, object]],
    impact_assessments: Sequence[Mapping[str, object]],
    risk_regime_updates: Sequence[Mapping[str, object]],
) -> list[str]:
    labels: list[str] = []
    for row in source_signals:
        labels.extend(_text_list(row.get("themes")))
    for row in market_events:
        labels.extend(_text_list(row.get("themes")))
    for row in segment_impacts:
        labels.append(str(row.get("segment_name") or ""))
    for row in impact_assessments:
        payload = row.get("payload")
        if isinstance(payload, Mapping):
            labels.extend(_text_list(payload.get("segments")))
            labels.extend(_text_list(payload.get("segment_exposure")))
    for row in risk_regime_updates:
        labels.extend(_text_list(row.get("affected_segments")))
    return _unique_texts(_label_text(label) for label in labels if _label_text(label))


def _advisory_stance(
    *,
    trading_advisories: Sequence[Mapping[str, object]],
    trade_plans: Sequence[Mapping[str, object]],
    evidence_ids: Sequence[str],
    market_events: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    advisory = trading_advisories[0] if trading_advisories else {}
    action = _normalize_stance_action(advisory.get("analyst_action"))
    freshness = _advisory_freshness(advisory)
    blocked = _advisory_blocked(advisory) or _trade_plan_blocked(trade_plans)
    if not advisory:
        action = "unrated"
        freshness = "missing"
    elif blocked:
        action = "review"
        freshness = "suppressed"
    elif freshness == "stale":
        action = "review"
    elif not evidence_ids:
        action = "unrated"
        freshness = "missing_evidence"

    return {
        "action": action,
        "tone": _stance_tone(action, blocked=blocked),
        "confidence": _stance_confidence(
            advisory=advisory,
            market_events=market_events,
            blocked=blocked,
            evidence_ids=evidence_ids,
        ),
        "freshness": freshness,
        "source_advisory_id": advisory.get("advisory_id") if advisory else None,
        "evidence_ids": _unique_texts(
            _text_list(advisory.get("evidence_ids")) if advisory else evidence_ids
        )
        or list(evidence_ids),
        "model_run_ids": _text_list(advisory.get("model_run_ids")),
        "deterministic_check_ids": _text_list(advisory.get("deterministic_checks")),
        "advisory_only": True,
    }


def _advisory_blocked(advisory: Mapping[str, object]) -> bool:
    payload = advisory.get("payload")
    if not isinstance(payload, Mapping):
        return False
    readiness = payload.get("readiness")
    if isinstance(readiness, Mapping) and readiness.get("publishable") is False:
        return True
    for key in ("publication_status", "status", "suppression_state"):
        if str(payload.get(key) or "").lower() in {"suppressed", "blocked"}:
            return True
    return _bool(payload.get("suppressed"))


def _trade_plan_blocked(trade_plans: Sequence[Mapping[str, object]]) -> bool:
    for plan in trade_plans:
        readiness = str(plan.get("readiness") or "").lower()
        if readiness in {"blocked", "stale", "invalidated"}:
            return True
    return False


def _advisory_freshness(advisory: Mapping[str, object]) -> str:
    payload = advisory.get("payload")
    if isinstance(payload, Mapping):
        for key in ("freshness", "freshness_status", "data_freshness"):
            value = str(payload.get(key) or "").lower()
            if value:
                return "stale" if "stale" in value else value
        readiness = payload.get("readiness")
        if isinstance(readiness, Mapping):
            reasons = " ".join(_text_list(readiness.get("blocking_reasons"))).lower()
            if "stale" in reasons:
                return "stale"
    return "current" if advisory else "missing"


def _normalize_stance_action(value: object) -> str:
    action = str(value or "unrated").strip().lower()
    allowed = {
        "watch",
        "accumulate",
        "hold",
        "trim",
        "avoid",
        "exit-candidate",
        "review",
        "unrated",
    }
    return action if action in allowed else "review"


def _stance_tone(action: str, *, blocked: bool) -> str:
    if blocked:
        return "mixed"
    if action == "accumulate":
        return "positive"
    if action in {"trim", "exit-candidate"}:
        return "cautious"
    if action == "avoid":
        return "negative"
    if action == "review":
        return "mixed"
    return "neutral"


def _stance_confidence(
    *,
    advisory: Mapping[str, object],
    market_events: Sequence[Mapping[str, object]],
    blocked: bool,
    evidence_ids: Sequence[str],
) -> str:
    if blocked or not advisory or not evidence_ids:
        return "low"
    event_confidences = {str(event.get("confidence") or "").lower() for event in market_events}
    if "high" in event_confidences:
        return "high"
    if "medium" in event_confidences or _text_list(advisory.get("deterministic_checks")):
        return "medium"
    return "review"


def _related_tickers(
    *,
    ticker: str,
    theme_label: str,
    segment_impacts: Sequence[Mapping[str, object]],
    market_events: Sequence[Mapping[str, object]],
    evidence_ids: Sequence[str],
) -> list[dict[str, object]]:
    related: list[dict[str, object]] = []
    for segment in segment_impacts:
        for related_ticker in _text_list(segment.get("primary_tickers")):
            if related_ticker != ticker:
                related.append(
                    _related_ticker_payload(
                        related_ticker,
                        "same_segment_primary",
                        f"Primary ticker in {theme_label}.",
                        evidence_ids,
                    )
                )
        for related_ticker in _text_list(segment.get("second_order_tickers")):
            if related_ticker != ticker:
                related.append(
                    _related_ticker_payload(
                        related_ticker,
                        "same_segment_second_order",
                        f"Second-order ticker linked through {theme_label}.",
                        evidence_ids,
                    )
                )
    for event in market_events:
        for related_ticker in _text_list(event.get("tickers")):
            if related_ticker != ticker:
                related.append(
                    _related_ticker_payload(
                        related_ticker,
                        "shared_market_event",
                        f"Appears in MarketEvent {event.get('event_id')}.",
                        _text_list(event.get("evidence_ids")),
                    )
                )
    deduped: dict[str, dict[str, object]] = {}
    for item in related:
        deduped.setdefault(str(item["ticker"]), item)
    return list(deduped.values())[:8]


def _related_ticker_payload(
    ticker: str,
    relationship_type: str,
    reason: str,
    evidence_ids: Sequence[str],
) -> dict[str, object]:
    return {
        "ticker": ticker,
        "relationship_type": relationship_type,
        "reason": reason,
        "evidence_ids": list(evidence_ids),
        "relevance": {
            "score": 0.72,
            "level": "supporting",
            "reason": reason,
        },
    }


def _risk_flags(*collections: Sequence[Mapping[str, object]]) -> list[str]:
    values: list[object] = []
    for collection in collections:
        for row in collection:
            values.extend(_text_list(row.get("risk_flags")))
            values.extend(
                value
                for value in (
                    row.get("risk_type"),
                    row.get("severity"),
                    row.get("status"),
                )
                if value
            )
            values.extend(_text_list(row.get("blocking_reasons")))
    return _unique_texts(values)


def _next_watch_items(
    assessments: Sequence[Mapping[str, object]],
    risks: Sequence[Mapping[str, object]],
    trade_plans: Sequence[Mapping[str, object]],
    market_events: Sequence[Mapping[str, object]],
) -> list[str]:
    items: list[object] = []
    for assessment in assessments:
        items.extend(_text_list(assessment.get("watch_items")))
    for risk in risks:
        items.append(risk.get("relief_condition"))
        items.append(risk.get("portfolio_monitoring_note"))
    for plan in trade_plans:
        items.extend(_text_list(plan.get("blocking_reasons")))
        if plan.get("readiness"):
            items.append(f"Trade plan readiness: {plan.get('readiness')}")
    for event in market_events[:2]:
        if event.get("catalyst"):
            items.append(f"Review catalyst: {event.get('catalyst')}")
    return _unique_texts(items)[:8]


def _trade_plan_note(plan: Mapping[str, object]) -> dict[str, object]:
    if not plan.get("trade_plan_id"):
        return {}
    return {
        "trade_plan_id": plan.get("trade_plan_id"),
        "readiness": plan.get("readiness"),
        "blocking_reasons": _text_list(plan.get("blocking_reasons")),
        "manual_journal_only": _bool(plan.get("manual_journal_only")),
        "evidence_ids": _text_list(plan.get("evidence_ids")),
        "deterministic_check_ids": _text_list(plan.get("deterministic_check_ids")),
        "last_reviewed_at": plan.get("last_reviewed_at"),
        "relevance": {
            "score": 0.66,
            "level": "supporting",
            "reason": "Trade plan is linked to the ticker workbench context.",
        },
    }


def _why_now(
    market_events: Sequence[Mapping[str, object]],
    advisories: Sequence[Mapping[str, object]],
    assessments: Sequence[Mapping[str, object]],
) -> str:
    for event in market_events:
        value = str(event.get("catalyst") or "").strip()
        if value:
            return value
    for advisory in advisories:
        value = str(advisory.get("advisory_summary") or "").strip()
        if value:
            return value
    for assessment in assessments:
        value = str(assessment.get("assessment") or "").strip()
        if value:
            return value
    return "No validated catalyst is available for this theme."


def _what_changed(
    source_signals: Sequence[Mapping[str, object]],
    market_events: Sequence[Mapping[str, object]],
) -> str:
    for signal in source_signals:
        value = str(signal.get("title") or "").strip()
        if value:
            return value
    for event in market_events:
        value = str(event.get("ai_relevance") or event.get("catalyst") or "").strip()
        if value:
            return value
    return "No validated source delta is available."


def _with_relevance(
    item: Mapping[str, object], *, level: str, reason: str
) -> dict[str, object]:
    payload = dict(item)
    payload["relevance"] = {
        "score": 0.86 if level == "direct" else 0.62,
        "level": level,
        "reason": reason,
    }
    return payload


def _evidence_union(*collections: Sequence[Mapping[str, object]]) -> list[str]:
    return _unique_texts(
        evidence_id
        for collection in collections
        for row in collection
        for evidence_id in (
            _text_list(row.get("evidence_ids"))
            + _text_list(row.get("source_evidence_ids"))
        )
    )


def _has_theme(row: Mapping[str, object], theme: str) -> bool:
    return (
        any(_same_theme(item, theme) for item in _text_list(row.get("themes")))
        or _same_theme(row.get("segment_name"), theme)
        or _theme_text(theme) in _theme_text(row.get("title"))
        or _theme_text(theme) in _theme_text(row.get("catalyst"))
        or _theme_text(theme) in _theme_text(row.get("assessment"))
    )


def _invalidation(
    assessments: Sequence[Mapping[str, object]],
    risk_regime_updates: Sequence[Mapping[str, object]],
) -> str | None:
    for row in assessments:
        value = row.get("invalidation")
        if isinstance(value, str) and value:
            return value
    for row in risk_regime_updates:
        value = row.get("invalidation_condition")
        if isinstance(value, str) and value:
            return value
    return None


def _latest_available_at(*collections: Sequence[Mapping[str, object]]) -> str | None:
    values = [
        timestamp
        for collection in collections
        for row in collection
        for timestamp in (
            _iso_or_none(row.get("available_at")),
            _iso_or_none(row.get("created_at")),
            _iso_or_none(row.get("last_reviewed_at")),
        )
        if timestamp is not None
    ]
    return max(values) if values else None


def _overlaps(left: Sequence[str], right: Sequence[str]) -> bool:
    return bool(set(left) & set(right))


def _same_theme(left: object, right: object) -> bool:
    left_text = _theme_text(left)
    right_text = _theme_text(right)
    return bool(
        left_text
        and right_text
        and (left_text == right_text or left_text in right_text or right_text in left_text)
    )


def _label_text(value: object) -> str:
    text = str(value or "").strip().replace("_", " ")
    return " ".join(part.capitalize() for part in text.split())


def _theme_text(value: object) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def _theme_id(label: str) -> str:
    text = "".join(
        character.lower() if character.isalnum() else "_"
        for character in label.strip()
    ).strip("_")
    while "__" in text:
        text = text.replace("__", "_")
    return text or "theme"


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


def _unique_texts(values: Iterable[object] | object) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    iterable = (
        (values,)
        if isinstance(values, str) or not isinstance(values, Iterable)
        else values
    )
    for value in iterable:
        if value is None:
            continue
        text = str(value)
        if not text or text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes"}
    return bool(value)


def _iso_or_none(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


__all__ = ["AdvisoryWorkstationRepository"]
