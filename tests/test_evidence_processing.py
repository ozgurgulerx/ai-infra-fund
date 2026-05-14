from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
sys.path.insert(0, str(CORE_SRC))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.contracts.evidence import EvidenceItem  # noqa: E402
from ai_infra_fund_core.evidence.chunking import chunk_evidence_text  # noqa: E402
from ai_infra_fund_core.evidence.hashing import compute_content_hash  # noqa: E402
from ai_infra_fund_core.evidence.provenance import build_evidence_item  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)


class EvidenceProcessingTests(unittest.TestCase):
    def test_content_hash_is_stable_and_metadata_key_order_independent(self) -> None:
        first = compute_content_hash(
            "GPU supply constraints increased lead times.",
            metadata={
                "source": {"publisher": "Example Research", "uri": "https://example.test/report"},
                "tickers": ["NVDA", "AMD"],
            },
        )
        second = compute_content_hash(
            "GPU supply constraints increased lead times.",
            metadata={
                "tickers": ["NVDA", "AMD"],
                "source": {"uri": "https://example.test/report", "publisher": "Example Research"},
            },
        )
        changed = compute_content_hash(
            "GPU supply constraints eased.",
            metadata={
                "source": {"publisher": "Example Research", "uri": "https://example.test/report"},
                "tickers": ["NVDA", "AMD"],
            },
        )

        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertEqual(64, len(first))

    def test_build_evidence_item_uses_existing_contract_and_stable_content_hash(self) -> None:
        item = build_evidence_item(
            text="NVDA reported stronger data-center demand.",
            source_uri="https://example.test/filing",
            source_type="filing",
            title="Quarterly filing",
            publisher="Example Issuer",
            author=None,
            published_at=NOW,
            ingested_at=NOW,
            license_label="public",
            data_class=DataClass.PUBLIC_EVIDENCE,
            tickers=("nvda",),
            themes=("ai infrastructure",),
            summary=None,
            storage_uri=None,
        )

        self.assertIsInstance(item, EvidenceItem)
        self.assertEqual(compute_content_hash("NVDA reported stronger data-center demand."), item.content_hash)
        self.assertEqual(f"evidence:{item.content_hash[:16]}", item.evidence_id)
        self.assertEqual(("NVDA",), item.tickers)
        self.assertEqual(("ai infrastructure",), item.themes)
        self.assertEqual(DataClass.PUBLIC_EVIDENCE, item.data_class)
        self.assertEqual(NOW, item.created_at)

    def test_chunking_is_deterministic_with_stable_span_refs(self) -> None:
        text = "ABCDEFGHIJ0123456789KLMNOPQRST"

        first = chunk_evidence_text(
            evidence_id="evidence-1",
            text=text,
            max_chars=10,
            embedding_model="local-test-embedding",
        )
        second = chunk_evidence_text(
            evidence_id="evidence-1",
            text=text,
            max_chars=10,
            embedding_model="local-test-embedding",
        )

        self.assertEqual(first, second)
        self.assertEqual(["ABCDEFGHIJ", "0123456789", "KLMNOPQRST"], [chunk.chunk_text for chunk in first])
        self.assertEqual(["char:0-10", "char:10-20", "char:20-30"], [chunk.span_ref for chunk in first])

    def test_chunks_include_required_fields_and_null_embedding(self) -> None:
        chunks = chunk_evidence_text(
            evidence_id="evidence-1",
            text="abcabc",
            max_chars=3,
            embedding_model="local-test-embedding",
        )

        self.assertEqual(2, len(chunks))
        self.assertEqual([0, 1], [chunk.chunk_index for chunk in chunks])
        self.assertEqual(["abc", "abc"], [chunk.chunk_text for chunk in chunks])
        self.assertEqual(["char:0-3", "char:3-6"], [chunk.span_ref for chunk in chunks])
        self.assertEqual(["evidence-1", "evidence-1"], [chunk.evidence_id for chunk in chunks])
        self.assertEqual(["local-test-embedding", "local-test-embedding"], [chunk.embedding_model for chunk in chunks])
        self.assertEqual([None, None], [chunk.embedding for chunk in chunks])
        self.assertEqual(len({chunk.chunk_id for chunk in chunks}), len(chunks))
        self.assertEqual(len({chunk.content_hash for chunk in chunks}), len(chunks))
        for chunk in chunks:
            self.assertTrue(chunk.chunk_id.startswith("chunk:"))
            self.assertEqual(64, len(chunk.content_hash))

    def test_processing_modules_do_not_import_cloud_clients_or_execution_surfaces(self) -> None:
        forbidden = [
            "from azure",
            "import azure",
            "from openai",
            "import openai",
            "from anthropic",
            "import anthropic",
            "place_order",
            "submit_order",
            "broker_client",
            "live_order",
            "order_execution",
        ]
        paths = [
            CORE_SRC / "ai_infra_fund_core" / "evidence" / "hashing.py",
            CORE_SRC / "ai_infra_fund_core" / "evidence" / "chunking.py",
            CORE_SRC / "ai_infra_fund_core" / "evidence" / "provenance.py",
        ]

        offenders: list[str] = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


if __name__ == "__main__":
    unittest.main()
