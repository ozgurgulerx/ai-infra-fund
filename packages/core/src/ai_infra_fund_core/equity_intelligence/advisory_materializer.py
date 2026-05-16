from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json

from ai_infra_fund_core.contracts.common import require_aware_datetime, require_text


DEFAULT_CONFIDENCE = "0.60"
DEFAULT_REVIEW_STATUS = "deterministic"
DEFAULT_THEME = "ai_infrastructure"


@dataclass(frozen=True, slots=True)
class CanonicalSourceSignalRecord:
    signal_id: str
    source_type: str
    signal_category: str
    title: str
    observed_at: datetime
    available_at: datetime
    tickers: tuple[str, ...]
    themes: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    derived_market_event_ids: tuple[str, ...]
    confidence: str
    review_status: str
    content_hash: str
    payload: dict[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CanonicalMarketEventRecord:
    event_id: str
    event_type: str
    source_signal_ids: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    tickers: tuple[str, ...]
    companies: tuple[str, ...]
    themes: tuple[str, ...]
    catalyst: str
    ai_relevance: str
    direction: str
    time_horizon: str
    confidence: str
    occurred_at: datetime
    available_at: datetime
    content_hash: str
    extracted_by_model_run_id: str | None
    review_status: str
    payload: dict[str, object]
    created_at: datetime


@dataclass(frozen=True, slots=True)
class CrawlAdvisoryMaterialization:
    source_signals: tuple[CanonicalSourceSignalRecord, ...]
    market_events: tuple[CanonicalMarketEventRecord, ...]


def materialize_crawl_advisory_records(
    *,
    capture: object,
    equity_events: Sequence[object],
    frontier_metadata: Mapping[str, object] | None = None,
) -> CrawlAdvisoryMaterialization:
    metadata = dict(frontier_metadata or {})
    source_signals: list[CanonicalSourceSignalRecord] = []
    market_events: list[CanonicalMarketEventRecord] = []

    for event in equity_events:
        source_signal, market_event = _materialize_one(
            capture=capture,
            event=event,
            frontier_metadata=metadata,
        )
        source_signals.append(source_signal)
        market_events.append(market_event)

    return CrawlAdvisoryMaterialization(
        source_signals=tuple(source_signals),
        market_events=tuple(market_events),
    )


def _materialize_one(
    *,
    capture: object,
    event: object,
    frontier_metadata: Mapping[str, object],
) -> tuple[CanonicalSourceSignalRecord, CanonicalMarketEventRecord]:
    ticker = require_text(str(getattr(event, "ticker", "")), "ticker").upper()
    event_id = require_text(getattr(event, "event_id", None), "event_id")
    event_type = require_text(getattr(event, "event_type", None), "event_type")
    summary = require_text(getattr(event, "summary", None), "summary").strip()
    event_time = require_aware_datetime(getattr(event, "event_time"), "event_time")
    available_at = require_aware_datetime(
        getattr(event, "available_at"), "available_at"
    )
    created_at = require_aware_datetime(getattr(event, "created_at"), "created_at")
    capture_id = require_text(getattr(capture, "capture_id", None), "capture_id")
    source_url = require_text(getattr(capture, "url", None), "url")
    capture_hash = require_text(getattr(capture, "content_hash", None), "content_hash")
    source_id = require_text(getattr(capture, "source_id", None), "source_id")
    source_kind = _source_kind(event=event, frontier_metadata=frontier_metadata)
    evidence_ids = _evidence_ids(event, capture_id)
    themes = _themes(frontier_metadata)
    company = _company_name(frontier_metadata, ticker)
    review_status = str(
        getattr(event, "review_status", None) or DEFAULT_REVIEW_STATUS
    ).strip()
    confidence = _confidence(event, frontier_metadata)
    market_event_id = f"market-{event_id}"
    signal_id = f"source-signal-{_hash('source-signal', event_id, capture_id)[:20]}"

    common_payload = {
        "capture_id": capture_id,
        "frontier_url_id": _optional_attr(capture, "frontier_url_id"),
        "source_id": source_id,
        "source_url": source_url,
        "source_kind": source_kind,
        "source_content_hash": capture_hash,
        "legacy_event_id": event_id,
        "legacy_event_type": event_type,
        "legacy_event_content_hash": _optional_attr(event, "content_hash"),
        "evidence_ids": list(evidence_ids),
        "advisory_label": "advisory_only",
    }

    source_signal = CanonicalSourceSignalRecord(
        signal_id=signal_id,
        source_type=source_kind,
        signal_category=event_type,
        title=summary,
        observed_at=event_time,
        available_at=available_at,
        tickers=(ticker,),
        themes=themes,
        evidence_ids=evidence_ids,
        derived_market_event_ids=(market_event_id,),
        confidence=confidence,
        review_status=review_status,
        content_hash=capture_hash,
        payload=dict(common_payload),
        created_at=created_at,
    )
    market_event = CanonicalMarketEventRecord(
        event_id=market_event_id,
        event_type=_market_event_type(event_type),
        source_signal_ids=(signal_id,),
        evidence_ids=evidence_ids,
        tickers=(ticker,),
        companies=(company,),
        themes=themes,
        catalyst=summary,
        ai_relevance=_ai_relevance(source_kind=source_kind, event_type=event_type),
        direction="unknown",
        time_horizon="review_needed",
        confidence=confidence,
        occurred_at=event_time,
        available_at=available_at,
        content_hash=capture_hash,
        extracted_by_model_run_id=_first_text(getattr(event, "model_run_ids", ())),
        review_status=review_status,
        payload=dict(common_payload),
        created_at=created_at,
    )
    return source_signal, market_event


def _source_kind(
    *,
    event: object,
    frontier_metadata: Mapping[str, object],
) -> str:
    for key in ("source_kind", "source_type", "provider_source_id"):
        value = frontier_metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    event_metadata = getattr(event, "metadata", {})
    if isinstance(event_metadata, Mapping):
        source_id = event_metadata.get("source_id")
        if isinstance(source_id, str) and source_id.strip():
            return source_id.strip()
    return "company_ir_press"


def _evidence_ids(event: object, capture_id: str) -> tuple[str, ...]:
    raw_ids = getattr(event, "evidence_ids", None) or ()
    if isinstance(raw_ids, str):
        raise ValueError("evidence_ids must be an iterable, not a string")
    values = tuple(str(value).strip() for value in raw_ids if str(value).strip())
    if values:
        return values
    return (f"evidence-{capture_id}",)


def _themes(frontier_metadata: Mapping[str, object]) -> tuple[str, ...]:
    raw_themes = frontier_metadata.get("themes")
    if isinstance(raw_themes, str):
        values = (raw_themes,)
    elif isinstance(raw_themes, Sequence):
        values = tuple(str(value) for value in raw_themes)
    else:
        values = ()
    normalized = tuple(value.strip() for value in values if value.strip())
    return normalized or (DEFAULT_THEME,)


def _company_name(frontier_metadata: Mapping[str, object], ticker: str) -> str:
    value = frontier_metadata.get("company_name")
    if isinstance(value, str) and value.strip():
        return value.strip()
    return ticker


def _confidence(event: object, frontier_metadata: Mapping[str, object]) -> str:
    event_metadata = getattr(event, "metadata", {})
    if isinstance(event_metadata, Mapping):
        value = event_metadata.get("confidence")
        if value is not None and str(value).strip():
            return str(value).strip()
    value = frontier_metadata.get("confidence")
    if value is not None and str(value).strip():
        return str(value).strip()
    return DEFAULT_CONFIDENCE


def _market_event_type(event_type: str) -> str:
    mapping = {
        "company_ir_press": "customer_adoption_signal",
        "news_alert": "competitive_position_signal",
        "sec_filing_published": "valuation_context_signal",
    }
    return mapping.get(event_type, event_type)


def _ai_relevance(*, source_kind: str, event_type: str) -> str:
    return (
        "Configured public-source crawl produced an AI infrastructure "
        f"advisory signal from {source_kind} ({event_type})."
    )


def _optional_attr(record: object, field_name: str) -> object:
    return getattr(record, field_name, None)


def _first_text(values: object) -> str | None:
    if isinstance(values, str):
        return values.strip() or None
    if isinstance(values, Sequence):
        for value in values:
            text = str(value).strip()
            if text:
                return text
    return None


def _hash(*parts: str) -> str:
    encoded = json.dumps(parts, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


__all__ = [
    "CanonicalMarketEventRecord",
    "CanonicalSourceSignalRecord",
    "CrawlAdvisoryMaterialization",
    "materialize_crawl_advisory_records",
]
