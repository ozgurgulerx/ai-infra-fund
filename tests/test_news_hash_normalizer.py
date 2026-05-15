from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))


class NewsContentHashTests(unittest.TestCase):
    def test_identical_inputs_produce_same_hash(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        a = news_content_hash(title="NVDA beats Q1 estimates", body="Revenue rose 70%.")
        b = news_content_hash(title="NVDA beats Q1 estimates", body="Revenue rose 70%.")
        self.assertEqual(a, b)
        self.assertEqual(64, len(a))

    def test_whitespace_and_casing_differences_collide(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        a = news_content_hash(title="NVDA beats Q1 estimates", body="Revenue rose 70%.")
        b = news_content_hash(
            title="  nvda   beats   q1   ESTIMATES  ", body="REVENUE\trose\n70%."
        )
        self.assertEqual(a, b)

    def test_trailing_punctuation_differences_collide(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        a = news_content_hash(title="NVDA beats Q1 estimates", body="Revenue rose.")
        b = news_content_hash(title="NVDA beats Q1 estimates!!!", body="Revenue rose")
        self.assertEqual(a, b)

    def test_different_titles_diverge(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        a = news_content_hash(title="NVDA beats Q1 estimates", body="Revenue rose 70%.")
        b = news_content_hash(
            title="NVDA misses Q1 estimates", body="Revenue rose 70%."
        )
        self.assertNotEqual(a, b)

    def test_long_body_truncated_to_500_chars(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        prefix = "A" * 500
        a = news_content_hash(title="t", body=prefix + "X" * 100)
        b = news_content_hash(title="t", body=prefix + "Y" * 100)
        self.assertEqual(a, b)

    def test_first_500_chars_changes_matter(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        a = news_content_hash(title="t", body="X" + "A" * 499)
        b = news_content_hash(title="t", body="Y" + "A" * 499)
        self.assertNotEqual(a, b)

    def test_empty_title_still_returns_hash(self) -> None:
        from ai_infra_fund_core.equity_intelligence.news_hash import (
            news_content_hash,
        )

        self.assertEqual(64, len(news_content_hash(title="", body="something")))


if __name__ == "__main__":
    unittest.main()
