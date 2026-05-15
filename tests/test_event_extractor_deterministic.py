from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.equity_intelligence.event_extractor import (  # noqa: E402
    EquityEventRecord,
    extract_events,
)
from ai_infra_fund_core.equity_intelligence.extraction import (  # noqa: E402
    ExtractedDocument,
    RssItem,
)


FETCHED_AT = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
PUBLISHED = datetime(2026, 5, 13, 16, 0, tzinfo=timezone.utc)


class ExtractEventsFromRssTests(unittest.TestCase):
    def test_one_event_per_rss_item_news_alert(self) -> None:
        items = (
            RssItem(
                guid="nv-2026-q1-call",
                title="NVIDIA Sets Conference Call for Quarterly Results",
                link="https://nvidianews.nvidia.com/news/q1-call",
                published_at=PUBLISHED,
                summary="",
            ),
            RssItem(
                guid="nv-2026-blackwell-volume",
                title="NVIDIA Blackwell Now Shipping in Volume",
                link="https://nvidianews.nvidia.com/news/blackwell-volume",
                published_at=PUBLISHED,
                summary="",
            ),
        )

        events = extract_events(
            ticker="NVDA",
            source_id="source-host-nvidianews-nvidia-com",
            capture_id="capture-1",
            extracted=items,
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(2, len(events))
        for event in events:
            self.assertIsInstance(event, EquityEventRecord)
            self.assertEqual("NVDA", event.ticker)
            self.assertEqual("news_alert", event.event_type)
            self.assertEqual("deterministic", event.review_status)
            self.assertEqual([], event.model_run_ids)
            self.assertEqual([], event.evidence_claim_ids)
            self.assertEqual("capture-1", event.source_capture_id)
            self.assertEqual(PUBLISHED, event.event_time)
            self.assertEqual("low", event.severity)


class ExtractEventsFromHtmlTests(unittest.TestCase):
    def test_press_release_keyword_maps_to_company_ir_press(self) -> None:
        doc = ExtractedDocument(
            title="NVIDIA Press Release: Q1 Results",
            published_at=PUBLISHED,
            clean_text="NVIDIA today reported record revenue.",
            lang="en",
            chars=512,
            quality_score=0.6,
        )

        events = extract_events(
            ticker="NVDA",
            source_id="source-host-investor-nvidia-com",
            capture_id="capture-2",
            extracted=doc,
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(1, len(events))
        self.assertEqual("company_ir_press", events[0].event_type)
        self.assertEqual(PUBLISHED, events[0].event_time)
        self.assertEqual(FETCHED_AT, events[0].available_at)

    def test_filing_keyword_maps_to_sec_filing_published(self) -> None:
        doc = ExtractedDocument(
            title="NVIDIA Files Form 10-Q for Q1",
            published_at=PUBLISHED,
            clean_text="Quarterly report.",
            lang="en",
            chars=128,
            quality_score=0.4,
        )

        events = extract_events(
            ticker="NVDA",
            source_id="source-host-sec-gov",
            capture_id="capture-3",
            extracted=doc,
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(1, len(events))
        self.assertEqual("sec_filing_published", events[0].event_type)

    def test_falls_back_to_company_ir_press_for_unknown_html(self) -> None:
        doc = ExtractedDocument(
            title="NVIDIA Solutions Overview",
            published_at=None,
            clean_text="Products and platforms.",
            lang="en",
            chars=120,
            quality_score=0.2,
        )

        events = extract_events(
            ticker="NVDA",
            source_id="source-host-nvidia-com",
            capture_id="capture-4",
            extracted=doc,
            fetched_at=FETCHED_AT,
        )

        self.assertEqual(1, len(events))
        self.assertEqual("company_ir_press", events[0].event_type)
        # No published_at on the page — event_time falls back to fetched_at
        self.assertEqual(FETCHED_AT, events[0].event_time)


class ContentHashTests(unittest.TestCase):
    def test_content_hash_is_deterministic_for_same_inputs(self) -> None:
        items = (
            RssItem(
                guid="nv-x",
                title="X",
                link=None,
                published_at=PUBLISHED,
                summary="",
            ),
        )
        a = extract_events(
            ticker="NVDA",
            source_id="source",
            capture_id="capture",
            extracted=items,
            fetched_at=FETCHED_AT,
        )
        b = extract_events(
            ticker="NVDA",
            source_id="source",
            capture_id="capture",
            extracted=items,
            fetched_at=FETCHED_AT,
        )
        self.assertEqual(a[0].content_hash, b[0].content_hash)

    def test_content_hash_changes_when_summary_changes(self) -> None:
        a_items = (
            RssItem(guid="g", title="A", link=None, published_at=PUBLISHED, summary=""),
        )
        b_items = (
            RssItem(guid="g", title="B", link=None, published_at=PUBLISHED, summary=""),
        )
        a = extract_events(
            ticker="NVDA",
            source_id="source",
            capture_id="capture",
            extracted=a_items,
            fetched_at=FETCHED_AT,
        )
        b = extract_events(
            ticker="NVDA",
            source_id="source",
            capture_id="capture",
            extracted=b_items,
            fetched_at=FETCHED_AT,
        )
        self.assertNotEqual(a[0].content_hash, b[0].content_hash)


if __name__ == "__main__":
    unittest.main()
