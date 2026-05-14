from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_api.repositories.evidence import EvidenceChunk, EvidenceRepository  # noqa: E402
from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402
from ai_infra_fund_core.contracts.evidence import EvidenceItem  # noqa: E402


NOW = datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)
LATER = datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc)

EVIDENCE_ITEM_FIELDS = (
    "evidence_id",
    "source_uri",
    "source_type",
    "title",
    "publisher",
    "author",
    "published_at",
    "ingested_at",
    "content_hash",
    "license_label",
    "data_class",
    "tickers",
    "themes",
    "summary",
    "storage_uri",
    "created_at",
)

EVIDENCE_CHUNK_FIELDS = (
    "chunk_id",
    "evidence_id",
    "chunk_index",
    "chunk_text",
    "span_ref",
    "content_hash",
    "embedding_model",
    "embedding",
)


class EvidenceRepositoryTests(unittest.TestCase):
    def test_persists_evidence_item_with_parameterized_insert(self) -> None:
        connection = FakeConnection()
        item = evidence_item()

        saved = EvidenceRepository(connection).save_item(item)

        self.assertEqual(item, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO evidence.evidence_items", statement)
        self.assertNotIn(item.source_uri, statement)
        self.assertNotIn(item.content_hash, statement)
        self.assertNotIn(item.license_label, statement)
        self.assertEqual(
            (
                item.evidence_id,
                item.source_uri,
                item.source_type,
                item.title,
                item.publisher,
                item.author,
                item.published_at,
                item.ingested_at,
                item.content_hash,
                item.license_label,
                DataClass.PRIVATE_RESEARCH.value,
                ["NVDA", "TSM"],
                ["ai_accelerators"],
                item.summary,
                item.storage_uri,
                item.created_at,
            ),
            params,
        )

    def test_persists_evidence_chunk_with_null_embedding_for_now(self) -> None:
        connection = FakeConnection()
        chunk = evidence_chunk()

        saved = EvidenceRepository(connection).save_chunk(chunk)

        self.assertEqual(chunk, saved)
        self.assertEqual(1, connection.commit_count)
        statement, params = connection.cursor_instance.executions[0]
        self.assertIn("INSERT INTO evidence.evidence_chunks", statement)
        self.assertNotIn(chunk.chunk_text, statement)
        self.assertNotIn(chunk.content_hash, statement)
        self.assertNotIn(chunk.embedding_model, statement)
        self.assertEqual(
            (
                chunk.chunk_id,
                chunk.evidence_id,
                chunk.chunk_index,
                chunk.chunk_text,
                chunk.span_ref,
                chunk.content_hash,
                chunk.embedding_model,
                None,
            ),
            params,
        )

    def test_persists_item_and_chunks_in_one_transaction(self) -> None:
        connection = FakeConnection()
        item = evidence_item()
        chunks = (evidence_chunk(), evidence_chunk(chunk_id="chunk-2", chunk_index=1, content_hash="hash-chunk-2"))

        saved_item, saved_chunks = EvidenceRepository(connection).save_item_with_chunks(item, chunks)

        self.assertEqual(item, saved_item)
        self.assertEqual(chunks, saved_chunks)
        self.assertEqual(1, connection.commit_count)
        self.assertEqual(3, len(connection.cursor_instance.executions))
        item_statement, _item_params = connection.cursor_instance.executions[0]
        chunk_statement, _chunk_params = connection.cursor_instance.executions[1]
        self.assertIn("INSERT INTO evidence.evidence_items", item_statement)
        self.assertIn("INSERT INTO evidence.evidence_chunks", chunk_statement)

    def test_rejects_missing_required_evidence_item_provenance_before_execute(self) -> None:
        connection = FakeConnection()
        incomplete_item = evidence_item_record(license_label="")

        with self.assertRaisesRegex(ValueError, "license_label is required"):
            EvidenceRepository(connection).save_item(incomplete_item)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_rejects_missing_required_evidence_ingestion_timestamp_before_execute(self) -> None:
        connection = FakeConnection()
        incomplete_item = evidence_item_record(ingested_at=None)

        with self.assertRaisesRegex(ValueError, "ingested_at is required"):
            EvidenceRepository(connection).save_item(incomplete_item)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_rejects_applicable_file_evidence_without_storage_uri_before_execute(self) -> None:
        connection = FakeConnection()
        incomplete_item = evidence_item(storage_uri="")

        with self.assertRaisesRegex(ValueError, "storage_uri is required"):
            EvidenceRepository(connection).save_item(incomplete_item)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_rejects_missing_required_chunk_provenance_before_execute(self) -> None:
        connection = FakeConnection()
        incomplete_chunk = evidence_chunk_record(span_ref="")

        with self.assertRaisesRegex(ValueError, "span_ref is required"):
            EvidenceRepository(connection).save_chunk(incomplete_chunk)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)

    def test_rejects_non_null_chunk_embedding_until_embedding_pipeline_exists(self) -> None:
        connection = FakeConnection()
        chunk = evidence_chunk_record(embedding=[0.1, 0.2])

        with self.assertRaisesRegex(ValueError, "embedding must be None"):
            EvidenceRepository(connection).save_chunk(chunk)

        self.assertEqual(0, connection.commit_count)
        self.assertEqual([], connection.cursor_instance.executions)


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params or ()))

    def __enter__(self) -> "FakeCursor":
        return self

    def __exit__(self, *_exc: object) -> None:
        return None


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.commit_count = 0

    def cursor(self) -> FakeCursor:
        return self.cursor_instance

    def commit(self) -> None:
        self.commit_count += 1


def evidence_item(**overrides: object) -> EvidenceItem:
    data = {
        "evidence_id": "evidence-1",
        "source_uri": "file:///reports/semianalysis.md",
        "source_type": "report",
        "title": "AI Hardware Supply",
        "publisher": "SemiAnalysis",
        "author": None,
        "published_at": NOW,
        "ingested_at": LATER,
        "content_hash": "hash-evidence",
        "license_label": "user_supplied_private",
        "data_class": DataClass.PRIVATE_RESEARCH,
        "tickers": ("NVDA", "TSM"),
        "themes": ("ai_accelerators",),
        "summary": "HBM and accelerator supply constraints",
        "storage_uri": "local://data/raw/reports/private/report.md",
        "created_at": NOW,
    }
    data.update(overrides)
    return EvidenceItem(**data)


def evidence_item_record(**overrides: object) -> SimpleNamespace:
    item = evidence_item()
    data = {field: getattr(item, field) for field in EVIDENCE_ITEM_FIELDS}
    data.update(overrides)
    return SimpleNamespace(**data)


def evidence_chunk(**overrides: object) -> EvidenceChunk:
    data = {
        "chunk_id": "chunk-1",
        "evidence_id": "evidence-1",
        "chunk_index": 0,
        "chunk_text": "HBM supply remains constrained for leading AI accelerators.",
        "span_ref": "p1:l2-l5",
        "content_hash": "hash-chunk-1",
        "embedding_model": "bge-m3",
        "embedding": None,
    }
    data.update(overrides)
    return EvidenceChunk(**data)


def evidence_chunk_record(**overrides: object) -> SimpleNamespace:
    chunk = evidence_chunk()
    data = {field: getattr(chunk, field) for field in EVIDENCE_CHUNK_FIELDS}
    data.update(overrides)
    return SimpleNamespace(**data)


if __name__ == "__main__":
    unittest.main()
