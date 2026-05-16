from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.equity_intelligence.extraction import (  # noqa: E402
    ExtractedDocument,
    RssItem,
    extract,
    extract_html,
    extract_rss,
)


HTML_SAMPLE = b"""<!doctype html>
<html lang="en">
<head>
  <title>NVIDIA Announces Q1 Results</title>
  <meta name="article:published_time" content="2026-05-13T20:00:00Z" />
</head>
<body>
  <article>
    <h1>NVIDIA Announces Q1 Results</h1>
    <p>NVIDIA today reported record data center revenue of $22.5 billion,
       up 427% from a year ago. Demand for AI accelerators remains strong.
       The company continues to execute on the Blackwell roadmap.</p>
    <p>"We see continued demand across hyperscaler customers," said Jensen Huang,
       founder and CEO of NVIDIA. "Generative AI has created a new computing era."</p>
  </article>
</body>
</html>
"""


RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>NVIDIA Newsroom</title>
    <link>https://nvidianews.nvidia.com/</link>
    <item>
      <title>NVIDIA Sets Conference Call for Quarterly Results</title>
      <link>https://nvidianews.nvidia.com/news/q1-call</link>
      <guid>nv-2026-q1-call</guid>
      <pubDate>Wed, 14 May 2026 12:00:00 GMT</pubDate>
      <description>NVIDIA will host an earnings call on May 22.</description>
    </item>
    <item>
      <title>NVIDIA Blackwell Now Shipping in Volume</title>
      <link>https://nvidianews.nvidia.com/news/blackwell-volume</link>
      <guid>nv-2026-blackwell-volume</guid>
      <pubDate>Tue, 13 May 2026 16:00:00 GMT</pubDate>
      <description>Production ramp completed across major OEMs.</description>
    </item>
  </channel>
</rss>
"""


GDELT_JSON_SAMPLE = b"""{
  "articles": [
    {
      "title": "Microsoft expands AI datacenter lease in Texas",
      "url": "https://example.com/msft-ai-datacenter-lease",
      "sourceCountry": "United States"
    },
    {
      "title": "Nuclear PPA supports new AI campus",
      "url": "https://example.com/nuclear-ppa-ai-campus"
    }
  ]
}
"""


class ExtractHtmlTests(unittest.TestCase):
    def test_extracts_title_and_clean_text_from_html(self) -> None:
        doc = extract_html(HTML_SAMPLE, base_url="https://nvidianews.nvidia.com/")

        self.assertIsInstance(doc, ExtractedDocument)
        self.assertIn("NVIDIA", (doc.title or ""))
        self.assertIn("data center revenue", doc.clean_text.lower())
        self.assertGreater(doc.chars, 100)
        self.assertGreaterEqual(doc.quality_score, 0.0)
        self.assertLessEqual(doc.quality_score, 1.0)

    def test_quality_score_is_higher_for_long_well_structured_text(self) -> None:
        long_doc = extract_html(HTML_SAMPLE, base_url="https://nvidianews.nvidia.com/")
        thin_doc = extract_html(
            b"<html><body>tiny</body></html>", base_url="https://x.test/"
        )

        self.assertGreater(long_doc.quality_score, thin_doc.quality_score)


class ExtractRssTests(unittest.TestCase):
    def test_returns_items_with_guid_title_link_and_published_at(self) -> None:
        items = extract_rss(RSS_SAMPLE)

        self.assertEqual(2, len(items))
        for item in items:
            self.assertIsInstance(item, RssItem)
        guids = sorted(item.guid for item in items)
        self.assertEqual(["nv-2026-blackwell-volume", "nv-2026-q1-call"], guids)
        first_by_time = sorted(items, key=lambda i: i.published_at or "")
        self.assertEqual("nv-2026-blackwell-volume", first_by_time[0].guid)


class DispatchTests(unittest.TestCase):
    def test_dispatcher_routes_html_content_type(self) -> None:
        result = extract(
            "text/html; charset=utf-8", HTML_SAMPLE, base_url="https://x.test/"
        )
        self.assertIsInstance(result, ExtractedDocument)

    def test_dispatcher_routes_rss_xml_content_type(self) -> None:
        result = extract("application/rss+xml", RSS_SAMPLE, base_url="https://x.test/")
        self.assertIsInstance(result, tuple)
        self.assertEqual(2, len(result))
        self.assertIsInstance(result[0], RssItem)

    def test_dispatcher_falls_back_to_html_for_unknown_text(self) -> None:
        result = extract("text/plain", HTML_SAMPLE, base_url="https://x.test/")
        self.assertIsInstance(result, ExtractedDocument)

    def test_dispatcher_routes_json_article_lists_to_readable_document(self) -> None:
        result = extract(
            "application/json",
            GDELT_JSON_SAMPLE,
            base_url="https://api.gdeltproject.org/api/v2/doc/doc",
        )

        self.assertIsInstance(result, ExtractedDocument)
        doc = result
        self.assertEqual("Microsoft expands AI datacenter lease in Texas", doc.title)
        self.assertIn("Nuclear PPA supports new AI campus", doc.clean_text)
        self.assertNotIn('"articles"', doc.clean_text)


if __name__ == "__main__":
    unittest.main()
