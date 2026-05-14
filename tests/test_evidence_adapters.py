from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.evidence.adapters import (  # noqa: E402
    PdfAdapterUnavailableError,
    UnsafeLocalEvidencePathError,
    read_local_markdown_evidence,
    read_local_pdf_evidence,
    read_local_text_evidence,
)
from ai_infra_fund_core.evidence.hashing import compute_content_hash  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class LocalEvidenceAdapterTests(unittest.TestCase):
    def test_text_adapter_reads_content_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory)
            source_path = allowed_root / "private-note.txt"
            content = "GPU cluster power demand remains capacity constrained.\n"
            source_path.write_text(content, encoding="utf-8")

            document = read_local_text_evidence(
                source_path,
                allowed_root=allowed_root,
                title="Private AI capex note",
                publisher="Internal Research",
                author="Ozgur",
                published_at=NOW,
                ingested_at=NOW,
                license_label="private-research-use",
                tickers=("nvda",),
                themes=("ai infrastructure",),
                summary="Capacity note.",
            )

        expected_uri = source_path.resolve().as_uri()
        self.assertEqual(content, document.content)
        self.assertEqual(source_path.resolve(), document.path)
        self.assertEqual(expected_uri, document.source_metadata.source_uri)
        self.assertEqual("file", document.source_metadata.source_type)
        self.assertEqual(DataClass.PRIVATE_RESEARCH, document.source_metadata.data_class)
        self.assertTrue(document.source_metadata.local_only)

        item = document.evidence_item
        self.assertEqual(expected_uri, item.source_uri)
        self.assertEqual("file", item.source_type)
        self.assertEqual("Private AI capex note", item.title)
        self.assertEqual("Internal Research", item.publisher)
        self.assertEqual("Ozgur", item.author)
        self.assertEqual(NOW, item.published_at)
        self.assertEqual(NOW, item.ingested_at)
        self.assertEqual("private-research-use", item.license_label)
        self.assertEqual(DataClass.PRIVATE_RESEARCH, item.data_class)
        self.assertEqual(("NVDA",), item.tickers)
        self.assertEqual(("ai infrastructure",), item.themes)
        self.assertEqual("Capacity note.", item.summary)
        self.assertEqual(expected_uri, item.storage_uri)
        self.assertEqual(compute_content_hash(content), item.content_hash)
        self.assertEqual(f"evidence:{item.content_hash[:16]}", item.evidence_id)

    def test_markdown_adapter_preserves_source_uri_and_content_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory)
            source_path = allowed_root / "thesis.md"
            markdown = "# AI infrastructure\n\n- Power is a bottleneck.\n"
            source_path.write_text(markdown, encoding="utf-8")

            document = read_local_markdown_evidence(
                "thesis.md",
                allowed_root=allowed_root,
                title="AI infrastructure thesis",
                ingested_at=NOW,
                license_label="internal",
                data_class=DataClass.PUBLIC_EVIDENCE,
            )

        expected_uri = source_path.resolve().as_uri()
        self.assertEqual(markdown, document.content)
        self.assertEqual(expected_uri, document.source_metadata.source_uri)
        self.assertEqual(expected_uri, document.evidence_item.source_uri)
        self.assertEqual(expected_uri, document.evidence_item.storage_uri)
        self.assertEqual(compute_content_hash(markdown), document.evidence_item.content_hash)
        self.assertEqual(DataClass.PUBLIC_EVIDENCE, document.evidence_item.data_class)
        self.assertFalse(document.source_metadata.local_only)

    def test_pdf_adapter_uses_injected_text_extractor_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory)
            source_path = allowed_root / "report.pdf"
            source_path.write_bytes(b"%PDF-1.4\n")

            document = read_local_pdf_evidence(
                source_path,
                allowed_root=allowed_root,
                title="PDF report",
                ingested_at=NOW,
                license_label="private",
                text_extractor=lambda path: f"Extracted from {path.name}.",
            )

        self.assertEqual("Extracted from report.pdf.", document.content)
        self.assertEqual(compute_content_hash(document.content), document.evidence_item.content_hash)
        self.assertEqual(DataClass.PRIVATE_RESEARCH, document.evidence_item.data_class)
        self.assertTrue(document.source_metadata.local_only)

    def test_pdf_adapter_can_be_explicitly_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory)
            source_path = allowed_root / "report.pdf"
            source_path.write_bytes(b"%PDF-1.4\n")

            with self.assertRaises(PdfAdapterUnavailableError) as error:
                read_local_pdf_evidence(
                    source_path,
                    allowed_root=allowed_root,
                    title="PDF report",
                    ingested_at=NOW,
                    license_label="private",
                    enabled=False,
                )

        self.assertIn("disabled", str(error.exception))

    def test_missing_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            allowed_root = Path(directory)

            with self.assertRaises(FileNotFoundError):
                read_local_text_evidence(
                    "missing.txt",
                    allowed_root=allowed_root,
                    title="Missing",
                    ingested_at=NOW,
                    license_label="private",
                )

    def test_path_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            allowed_root = base / "allowed"
            allowed_root.mkdir()
            outside_path = base / "outside.txt"
            outside_path.write_text("outside", encoding="utf-8")

            with self.assertRaises(UnsafeLocalEvidencePathError):
                read_local_text_evidence(
                    "../outside.txt",
                    allowed_root=allowed_root,
                    title="Outside",
                    ingested_at=NOW,
                    license_label="private",
                )

    def test_adapter_module_has_no_cloud_model_scoring_or_execution_surface(self) -> None:
        source_text = (
            CORE_SRC / "ai_infra_fund_core" / "evidence" / "adapters.py"
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
            "live_order",
            "order_execution",
        ]

        offenders = [pattern for pattern in forbidden if pattern in source_text]
        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
