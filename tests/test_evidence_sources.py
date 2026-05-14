from __future__ import annotations

from dataclasses import fields, is_dataclass
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.evidence.sources import (  # noqa: E402
    EvidenceSourceMetadata,
    normalize_evidence_source_metadata,
)


class EvidenceSourceNormalizationTests(unittest.TestCase):
    def test_accepts_file_manual_and_public_uri_sources(self) -> None:
        cases = [
            (" file:///Users/example/research/report.pdf ", "file"),
            ("manual:semianalysis-note-2026-05-14", "manual"),
            ("https://example.com/public-filing", "public_uri"),
        ]

        for source_uri, expected_source_type in cases:
            with self.subTest(source_uri=source_uri):
                metadata = normalize_evidence_source_metadata(
                    source_uri=source_uri,
                    license_label="research-use",
                    data_class=DataClass.PUBLIC_EVIDENCE,
                )

                self.assertIsInstance(metadata, EvidenceSourceMetadata)
                self.assertTrue(is_dataclass(metadata))
                self.assertEqual(source_uri.strip(), metadata.source_uri)
                self.assertEqual(expected_source_type, metadata.source_type)
                self.assertEqual("research-use", metadata.license_label)
                self.assertEqual(DataClass.PUBLIC_EVIDENCE, metadata.data_class)

    def test_rejects_missing_required_source_metadata(self) -> None:
        valid = {
            "source_uri": "file:///Users/example/research/report.pdf",
            "license_label": "research-use",
            "data_class": DataClass.PUBLIC_EVIDENCE,
        }

        for field_name in ("source_uri", "license_label", "data_class"):
            with self.subTest(field_name=field_name):
                invalid = {**valid, field_name: ""}
                if field_name == "data_class":
                    invalid[field_name] = None

                with self.assertRaises(ValueError):
                    normalize_evidence_source_metadata(**invalid)

    def test_private_research_is_local_only_by_default(self) -> None:
        metadata = normalize_evidence_source_metadata(
            source_uri="file:///Users/example/private/paid-report.pdf",
            license_label="paid-private",
            data_class="private_research",
        )

        self.assertEqual(DataClass.PRIVATE_RESEARCH, metadata.data_class)
        self.assertTrue(metadata.local_only)

    def test_public_evidence_defaults_to_not_local_only(self) -> None:
        metadata = normalize_evidence_source_metadata(
            source_uri="https://example.com/public-filing",
            license_label="public",
            data_class="public_evidence",
        )

        self.assertEqual(DataClass.PUBLIC_EVIDENCE, metadata.data_class)
        self.assertFalse(metadata.local_only)

    def test_normalized_metadata_does_not_carry_semantic_portfolio_text(self) -> None:
        metadata_fields = {field.name for field in fields(EvidenceSourceMetadata)}

        self.assertNotIn("semantic_text", metadata_fields)
        self.assertNotIn("portfolio_holdings_text", metadata_fields)
        self.assertEqual(
            {"source_uri", "source_type", "license_label", "data_class", "local_only"},
            metadata_fields,
        )

    def test_source_module_has_no_cloud_model_or_execution_surface(self) -> None:
        source_text = (
            CORE_SRC / "ai_infra_fund_core" / "evidence" / "sources.py"
        ).read_text(encoding="utf-8")
        forbidden = [
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "model_id",
            "recommendation",
            "score",
            "place_order",
            "submit_order",
            "broker_client",
            "order_execution",
            "portfolio_holdings",
        ]

        offenders = [pattern for pattern in forbidden if pattern in source_text]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
