"""Deterministic event extraction.

Maps an `ExtractedDocument` or RSS `tuple[RssItem,...]` to the
`EquityEventRecord` shape expected by `EquityIntelligenceRepository`.

This is the v1 path — no LLM. Event type is decided by simple title keywords
and source type. The complementary `research_extractor.LLMClaimExtractor`
Protocol covers the eventual LLM path; today its only implementation is a
no-op stub.

Allowed event_type values (intentionally not part of `EquityEventType` enum;
that enum is reserved for downstream synthesized signals):
    - news_alert            -> from RSS feed items
    - sec_filing_published  -> HTML title matched 8-K / 10-Q / 10-K
    - company_ir_press      -> HTML title matched press / earnings / fallback
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from hashlib import sha256
from typing import cast

from .extraction import ExtractedDocument, RssItem


EVENT_TYPE_NEWS_ALERT = "news_alert"
EVENT_TYPE_SEC_FILING = "sec_filing_published"
EVENT_TYPE_COMPANY_IR = "company_ir_press"


_FILING_KEYWORDS = ("8-k", "8k", "10-q", "10q", "10-k", "10k", "form 4", "13f")
_PRESS_KEYWORDS = (
    "press release",
    "earnings",
    "quarterly results",
    "results",
    "announces",
)


@dataclass(frozen=True, slots=True)
class EquityEventRecord:
    event_id: str
    ticker: str
    event_type: str
    event_time: datetime
    available_at: datetime
    source_capture_id: str | None
    summary: str
    severity: str
    evidence_ids: list[str]
    evidence_claim_ids: list[str]
    model_run_ids: list[str]
    review_status: str
    metadata: dict[str, object]
    content_hash: str
    created_at: datetime


def extract_events(
    *,
    ticker: str,
    source_id: str,
    capture_id: str,
    extracted: ExtractedDocument | tuple[RssItem, ...],
    fetched_at: datetime,
) -> tuple[EquityEventRecord, ...]:
    if isinstance(extracted, tuple):
        return _from_rss(ticker, source_id, capture_id, extracted, fetched_at)
    return _from_html(ticker, source_id, capture_id, extracted, fetched_at)


def _from_rss(
    ticker: str,
    source_id: str,
    capture_id: str,
    items: tuple[RssItem, ...],
    fetched_at: datetime,
) -> tuple[EquityEventRecord, ...]:
    records: list[EquityEventRecord] = []
    for item in items:
        event_time = item.published_at or fetched_at
        summary = item.title or item.summary or item.guid
        content_hash = _hash(
            ticker, EVENT_TYPE_NEWS_ALERT, event_time, summary, item.guid
        )
        records.append(
            EquityEventRecord(
                event_id=f"event-{ticker.lower()}-{content_hash[:16]}",
                ticker=ticker,
                event_type=EVENT_TYPE_NEWS_ALERT,
                event_time=event_time,
                available_at=fetched_at,
                source_capture_id=capture_id,
                summary=summary,
                severity="low",
                evidence_ids=[],
                evidence_claim_ids=[],
                model_run_ids=[],
                review_status="deterministic",
                metadata={
                    "origin": "rss_feed",
                    "source_id": source_id,
                    "guid": item.guid,
                    "link": item.link or "",
                },
                content_hash=content_hash,
                created_at=fetched_at,
            )
        )
    return tuple(records)


def _from_html(
    ticker: str,
    source_id: str,
    capture_id: str,
    doc: ExtractedDocument,
    fetched_at: datetime,
) -> tuple[EquityEventRecord, ...]:
    if _is_non_event_page(doc):
        return ()

    title = (doc.title or "").strip()
    event_type = _classify_html(title)
    event_time = doc.published_at or fetched_at
    summary = title or (doc.clean_text or "")[:200] or "company_ir_capture"
    content_hash = _hash(ticker, event_type, event_time, summary, source_id)
    record = EquityEventRecord(
        event_id=f"event-{ticker.lower()}-{content_hash[:16]}",
        ticker=ticker,
        event_type=event_type,
        event_time=event_time,
        available_at=fetched_at,
        source_capture_id=capture_id,
        summary=summary,
        severity="low",
        evidence_ids=[],
        evidence_claim_ids=[],
        model_run_ids=[],
        review_status="deterministic",
        metadata={
            "origin": "html_capture",
            "source_id": source_id,
            "quality_score": doc.quality_score,
            "chars": doc.chars,
            "lang": doc.lang or "",
        },
        content_hash=content_hash,
        created_at=fetched_at,
    )
    return (record,)


def _classify_html(title: str) -> str:
    lowered = title.lower()
    if any(kw in lowered for kw in _FILING_KEYWORDS):
        return EVENT_TYPE_SEC_FILING
    if any(kw in lowered for kw in _PRESS_KEYWORDS):
        return EVENT_TYPE_COMPANY_IR
    return EVENT_TYPE_COMPANY_IR


def _is_non_event_page(doc: ExtractedDocument) -> bool:
    title = (doc.title or "").strip().lower()
    text = doc.clean_text.strip().lower()
    if not title and not text:
        return True
    if title.startswith(("{", "[")) or text.startswith(("{", "[")):
        return True
    if '"articles"' in text or '"results"' in text:
        return True
    if "google trends" in title:
        return True
    if title.startswith("get your apikey") or "get your apikey" in text:
        return True
    if "missing api_key" in text or "missing api key" in text:
        return True
    if "invalid api key" in text or "api key required" in text:
        return True
    if "validation_error" in text and "api_key" in text:
        return True
    if title.startswith("you searched for ") or title.startswith("search results"):
        return True
    if text.startswith("search results for "):
        return True
    return False


def _hash(ticker: str, event_type: str, when: datetime, summary: str, salt: str) -> str:
    payload = {
        "ticker": ticker,
        "event_type": event_type,
        "event_time": when.isoformat(),
        "summary": summary,
        "salt": salt,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return sha256(encoded).hexdigest()


__all__ = [
    "EVENT_TYPE_COMPANY_IR",
    "EVENT_TYPE_NEWS_ALERT",
    "EVENT_TYPE_SEC_FILING",
    "EquityEventRecord",
    "extract_events",
]
