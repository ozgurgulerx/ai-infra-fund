from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from ai_infra_fund_core.contracts.common import DataClass
from ai_infra_fund_core.contracts.evidence import EvidenceItem

from .hashing import compute_content_hash


def build_evidence_item(
    *,
    text: str | bytes,
    source_uri: str,
    source_type: str,
    title: str | None,
    publisher: str | None,
    author: str | None,
    published_at: datetime | None,
    ingested_at: datetime,
    license_label: str,
    data_class: DataClass | str,
    tickers: Iterable[str] | None,
    themes: Iterable[str] | None,
    summary: str | None,
    storage_uri: str | None,
    created_at: datetime | None = None,
) -> EvidenceItem:
    content_hash = compute_content_hash(text)
    return EvidenceItem(
        evidence_id=f"evidence:{content_hash[:16]}",
        source_uri=source_uri,
        source_type=source_type,
        title=title,
        publisher=publisher,
        author=author,
        published_at=published_at,
        ingested_at=ingested_at,
        content_hash=content_hash,
        license_label=license_label,
        data_class=data_class,
        tickers=tuple(tickers or ()),
        themes=tuple(themes or ()),
        summary=summary,
        storage_uri=storage_uri,
        created_at=created_at or ingested_at,
    )


__all__ = ["build_evidence_item"]
