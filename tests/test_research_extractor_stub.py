from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.equity_intelligence.extraction import ExtractedDocument  # noqa: E402
from ai_infra_fund_core.equity_intelligence.research_extractor import (  # noqa: E402
    CaptureContext,
    LLMClaimExtractor,
    ResearchExtractionResult,
    StubLLMClaimExtractor,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class ResearchExtractionResultTests(unittest.TestCase):
    def test_empty_result_construction(self) -> None:
        result = ResearchExtractionResult(claims=(), model_runs=())
        self.assertEqual((), result.claims)
        self.assertEqual((), result.model_runs)


class StubLLMClaimExtractorTests(unittest.TestCase):
    def test_returns_empty_result_without_network_calls(self) -> None:
        doc = ExtractedDocument(
            title="NVIDIA Q1",
            published_at=NOW,
            clean_text="x" * 500,
            lang="en",
            chars=500,
            quality_score=0.5,
        )
        context = CaptureContext(
            ticker="NVDA",
            source_id="source-1",
            capture_id="capture-1",
            url="https://x.test/",
            data_class="public_evidence",
            extracted=doc,
            fetched_at=NOW,
        )

        result = StubLLMClaimExtractor().extract_claims(
            capture=context, model_router=None
        )

        self.assertEqual((), result.claims)
        self.assertEqual((), result.model_runs)

    def test_stub_satisfies_protocol(self) -> None:
        extractor: LLMClaimExtractor = StubLLMClaimExtractor()
        self.assertTrue(callable(extractor.extract_claims))


class CaptureContextValidationTests(unittest.TestCase):
    def test_rejects_non_public_evidence_data_class(self) -> None:
        doc = ExtractedDocument(
            title="x",
            published_at=None,
            clean_text="y",
            lang=None,
            chars=1,
            quality_score=0.0,
        )
        with self.assertRaises(ValueError):
            CaptureContext(
                ticker="NVDA",
                source_id="source-1",
                capture_id="capture-1",
                url="https://x.test/",
                data_class="private_research",
                extracted=doc,
                fetched_at=NOW,
            )


if __name__ == "__main__":
    unittest.main()
