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
    EvidenceClaimDraft,
    LLMClaimExtractor,
    MarketEventDraft,
    ResearchExtractionResult,
    SourceSignalDraft,
    StubLLMClaimExtractor,
    SuppressedModelOutput,
    validate_model_draft_payload,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class ResearchExtractionResultTests(unittest.TestCase):
    def test_empty_result_construction(self) -> None:
        result = ResearchExtractionResult(
            evidence_claims=(),
            source_signal_drafts=(),
            market_event_drafts=(),
            model_runs=(),
            reviewer_findings=(),
            suppressed_outputs=(),
        )
        self.assertEqual((), result.evidence_claims)
        self.assertEqual((), result.source_signal_drafts)
        self.assertEqual((), result.market_event_drafts)
        self.assertEqual((), result.model_runs)
        self.assertEqual((), result.reviewer_findings)
        self.assertEqual((), result.suppressed_outputs)

    def test_allowed_draft_outputs_validate(self) -> None:
        claim = EvidenceClaimDraft(
            claim_id="claim-1",
            statement="NVIDIA reported higher data center revenue.",
            evidence_capture_id="capture-1",
            citation_url="https://example.test/nvidia-results",
            model_run_id="run-1",
        )
        signal = SourceSignalDraft(
            signal_id="signal-1",
            ticker="NVDA",
            source_id="source-1",
            summary="Public company IR page changed.",
            evidence_capture_id="capture-1",
            model_run_id="run-1",
        )
        event = MarketEventDraft(
            event_id="event-1",
            ticker="NVDA",
            event_type="company_ir_press",
            summary="Quarterly results were published.",
            evidence_capture_id="capture-1",
            model_run_id="run-1",
        )
        suppressed = SuppressedModelOutput(
            reason="forbidden_key",
            payload_key="score",
            excerpt="score: 0.9",
        )

        result = ResearchExtractionResult(
            evidence_claims=(claim,),
            source_signal_drafts=(signal,),
            market_event_drafts=(event,),
            model_runs=(),
            reviewer_findings=("citations present",),
            suppressed_outputs=(suppressed,),
        )

        self.assertEqual((claim,), result.evidence_claims)
        self.assertEqual((signal,), result.source_signal_drafts)
        self.assertEqual((event,), result.market_event_drafts)
        self.assertEqual(("citations present",), result.reviewer_findings)
        validate_model_draft_payload(
            {
                "evidence_claims": [{"statement": claim.statement}],
                "source_signal_drafts": [{"summary": signal.summary}],
                "market_event_drafts": [{"summary": event.summary}],
            }
        )

    def test_model_draft_payload_rejects_forbidden_keys_and_phrases(self) -> None:
        forbidden_payloads = [
            {"score": 0.91},
            {"target_weight": 0.15},
            {"constraint": "max position 20%"},
            {"order": {"ticker": "NVDA", "side": "buy"}},
            {"execution": {"venue": "NYSE"}},
            {"market_event_drafts": [{"summary": "Buy 100 shares immediately"}]},
            {"evidence_claims": [{"statement": "Set NVDA to a 12% portfolio weight"}]},
        ]

        for payload in forbidden_payloads:
            with self.subTest(payload=payload):
                with self.assertRaises(ValueError):
                    validate_model_draft_payload(payload)


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

        self.assertEqual((), result.evidence_claims)
        self.assertEqual((), result.source_signal_drafts)
        self.assertEqual((), result.market_event_drafts)
        self.assertEqual((), result.model_runs)
        self.assertEqual((), result.reviewer_findings)
        self.assertEqual((), result.suppressed_outputs)

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
