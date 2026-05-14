from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass, ModelRunStatus  # noqa: E402
from ai_infra_fund_core.contracts.evidence import EvidenceClaim, EvidenceItem  # noqa: E402
from ai_infra_fund_core.evidence.chunking import EvidenceChunk  # noqa: E402
from ai_infra_fund_core.evidence.claims import (  # noqa: E402
    ClaimExtractionModelContext,
    extract_claims_locally,
    extract_claims_with_model,
)


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class EvidenceClaimExtractionTests(unittest.TestCase):
    def test_local_stub_extracts_source_linked_evidence_claims(self) -> None:
        item = evidence_item(
            tickers=("NVDA",),
            themes=("ai_accelerators",),
            source_uri="https://example.test/nvda-demand",
            content_hash="a" * 64,
        )
        chunk = evidence_chunk(
            chunk_text="NVDA data-center demand grew into 2026 as AI accelerator deployments expanded.",
            span_ref="char:0-78",
        )

        claims = extract_claims_locally(
            evidence_item=item,
            chunks=(chunk,),
            created_at=NOW,
        )

        self.assertEqual(1, len(claims))
        claim = claims[0]
        self.assertIsInstance(claim, EvidenceClaim)
        self.assertTrue(claim.claim_id.startswith("claim:"))
        self.assertEqual(item.evidence_id, claim.evidence_id)
        self.assertEqual(chunk.chunk_id, claim.chunk_id)
        self.assertEqual("NVDA", claim.ticker_or_theme)
        self.assertEqual("demand_growth", claim.claim_type)
        self.assertEqual("positive", claim.direction)
        self.assertIsNone(claim.magnitude)
        self.assertEqual("2026", claim.time_horizon)
        self.assertEqual(Decimal("0.60"), claim.confidence)
        self.assertIn(chunk.chunk_id, claim.quote_or_span_ref)
        self.assertIn(chunk.span_ref, claim.quote_or_span_ref)
        self.assertIn(item.source_uri, claim.quote_or_span_ref)
        self.assertIn(item.content_hash, claim.quote_or_span_ref)
        self.assertIsNone(claim.extracted_by_model_run_id)
        self.assertIsNone(claim.validated_at)
        self.assertEqual(NOW, claim.created_at)

    def test_model_assisted_success_returns_claims_and_success_model_run(self) -> None:
        item = evidence_item(tickers=("NVDA",), data_class=DataClass.PUBLIC_EVIDENCE)
        chunk = evidence_chunk()
        context = model_context(
            allowed_data_classes=(DataClass.PUBLIC_EVIDENCE,),
            endpoint_type="azure_ai_foundry",
        )
        observed_prompts: list[object] = []

        def fake_model(prompt: object) -> dict[str, object]:
            observed_prompts.append(prompt)
            return {
                "claims": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "ticker_or_theme": "NVDA",
                        "claim_type": "demand_growth",
                        "direction": "positive",
                        "magnitude": None,
                        "time_horizon": "2026",
                        "confidence": "0.73",
                        "quote_or_span_ref": chunk.span_ref,
                    }
                ]
            }

        result = extract_claims_with_model(
            evidence_item=item,
            chunks=(chunk,),
            model_context=context,
            model_response_provider=fake_model,
            created_at=NOW,
        )

        self.assertEqual(1, len(observed_prompts))
        self.assertEqual(1, len(result.claims))
        self.assertEqual(1, len(result.model_runs))

        run = result.model_runs[0]
        self.assertEqual(ModelRunStatus.SUCCESS, run.status)
        self.assertTrue(run.model_run_id.startswith("model-run:"))
        self.assertEqual(context.task_role, run.task_role)
        self.assertEqual(context.model_id, run.model_id)
        self.assertEqual(context.deployment, run.deployment)
        self.assertEqual(context.provider, run.provider)
        self.assertEqual(context.prompt_version, run.prompt_version)
        self.assertEqual((DataClass.PUBLIC_EVIDENCE,), run.data_classes)
        self.assertEqual(64, len(run.input_hash))
        self.assertEqual(64, len(run.output_hash or ""))
        self.assertTrue(run.schema_valid)
        self.assertEqual(0, run.retry_count)
        self.assertIsNone(run.error_summary)

        claim = result.claims[0]
        self.assertEqual(run.model_run_id, claim.extracted_by_model_run_id)
        self.assertEqual(item.evidence_id, claim.evidence_id)
        self.assertEqual(chunk.chunk_id, claim.chunk_id)
        self.assertEqual("NVDA", claim.ticker_or_theme)
        self.assertEqual(Decimal("0.73"), claim.confidence)
        self.assertIn(item.source_uri, claim.quote_or_span_ref)
        self.assertIn(item.content_hash, claim.quote_or_span_ref)

    def test_model_assisted_failure_returns_failure_model_run_without_claims(self) -> None:
        item = evidence_item(data_class=DataClass.PUBLIC_EVIDENCE)
        context = model_context(
            allowed_data_classes=(DataClass.PUBLIC_EVIDENCE,),
            endpoint_type="azure_ai_foundry",
        )

        def failing_model(_prompt: object) -> dict[str, object]:
            raise RuntimeError("schema validation failed")

        result = extract_claims_with_model(
            evidence_item=item,
            chunks=(evidence_chunk(),),
            model_context=context,
            model_response_provider=failing_model,
            created_at=NOW,
        )

        self.assertEqual((), result.claims)
        self.assertEqual(1, len(result.model_runs))
        run = result.model_runs[0]
        self.assertEqual(ModelRunStatus.FAILURE, run.status)
        self.assertFalse(run.schema_valid)
        self.assertIsNone(run.output_hash)
        self.assertIn("schema validation failed", run.error_summary or "")
        self.assertEqual(context.model_id, run.model_id)

    def test_model_assisted_extraction_records_model_run_through_injected_recorder(self) -> None:
        item = evidence_item(tickers=("NVDA",), data_class=DataClass.PUBLIC_EVIDENCE)
        chunk = evidence_chunk()
        context = model_context(
            allowed_data_classes=(DataClass.PUBLIC_EVIDENCE,),
            endpoint_type="azure_ai_foundry",
        )
        recorded_runs: list[object] = []

        result = extract_claims_with_model(
            evidence_item=item,
            chunks=(chunk,),
            model_context=context,
            model_response_provider=lambda _prompt: {"claims": []},
            model_run_recorder=recorded_runs.append,
            created_at=NOW,
        )

        self.assertEqual(tuple(recorded_runs), result.model_runs)
        self.assertEqual(ModelRunStatus.SUCCESS, result.model_runs[0].status)

    def test_denied_cloud_private_research_creates_denied_run_and_no_claims(self) -> None:
        item = evidence_item(data_class=DataClass.PRIVATE_RESEARCH)
        context = model_context(
            allowed_data_classes=(DataClass.PUBLIC_EVIDENCE,),
            endpoint_type="azure_ai_foundry",
        )

        def forbidden_model(_prompt: object) -> dict[str, object]:
            raise AssertionError("private research must not be sent to cloud models")

        result = extract_claims_with_model(
            evidence_item=item,
            chunks=(evidence_chunk(),),
            model_context=context,
            model_response_provider=forbidden_model,
            created_at=NOW,
        )

        self.assertEqual((), result.claims)
        self.assertEqual(1, len(result.model_runs))
        run = result.model_runs[0]
        self.assertEqual(ModelRunStatus.DENIED, run.status)
        self.assertFalse(run.schema_valid)
        self.assertIsNone(run.output_hash)
        self.assertEqual((DataClass.PRIVATE_RESEARCH,), run.data_classes)
        self.assertIn("data-class policy denied cloud route", run.error_summary or "")
        self.assertEqual(context.model_id, run.model_id)


def evidence_item(**overrides: object) -> EvidenceItem:
    data = {
        "evidence_id": "evidence-1",
        "source_uri": "https://example.test/report",
        "source_type": "report",
        "title": "AI Infrastructure Demand",
        "publisher": "Example Research",
        "author": None,
        "published_at": NOW,
        "ingested_at": NOW,
        "content_hash": "b" * 64,
        "license_label": "public",
        "data_class": DataClass.PUBLIC_EVIDENCE,
        "tickers": ("NVDA",),
        "themes": ("ai_accelerators",),
        "summary": None,
        "storage_uri": None,
        "created_at": NOW,
    }
    data.update(overrides)
    return EvidenceItem(**data)


def evidence_chunk(**overrides: object) -> EvidenceChunk:
    data = {
        "chunk_id": "chunk-1",
        "evidence_id": "evidence-1",
        "chunk_index": 0,
        "chunk_text": "NVDA data-center demand grew into 2026.",
        "span_ref": "char:0-41",
        "content_hash": "c" * 64,
        "embedding_model": "local-test-embedding",
        "embedding": None,
    }
    data.update(overrides)
    return EvidenceChunk(**data)


def model_context(**overrides: object) -> ClaimExtractionModelContext:
    data = {
        "model_id": "configured-claim-model",
        "deployment": "configured-claim-deployment",
        "provider": "configured-provider",
        "endpoint_type": "local",
        "prompt_version": "claim-extraction-v1",
        "task_role": "evidence_claim_extraction",
        "allowed_data_classes": (DataClass.PUBLIC_EVIDENCE,),
    }
    data.update(overrides)
    return ClaimExtractionModelContext(**data)


if __name__ == "__main__":
    unittest.main()
