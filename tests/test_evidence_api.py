from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from ai_infra_fund_core.contracts.common import DataClass  # noqa: E402


class ManualEvidenceApiTests(unittest.TestCase):
    def test_accepts_valid_manual_private_research_and_persists_evidence(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeEvidenceRepository()
        app = main.create_app(evidence_repository=repository)

        response = TestClient(app).post(
            "/internal/evidence/manual",
            json={
                "source_uri": " HTTPS://Example.com/research/report.pdf?b=2&a=1#section ",
                "source_type": "manual_report",
                "license_label": "user_supplied_private",
                "data_class": "private_research",
                "text": ("AI infrastructure demand is rising.\n" * 80).strip(),
                "title": "AI infra channel checks",
                "tickers": ["nvda", "msft"],
                "themes": ["accelerated compute"],
            },
        )

        self.assertEqual(201, response.status_code)
        payload = response.json()["data"]
        self.assertTrue(payload["evidence_id"].startswith("evidence-"))
        self.assertEqual(64, len(payload["content_hash"]))
        self.assertGreaterEqual(payload["chunk_count"], 1)
        self.assertTrue(payload["local_only"])
        self.assertEqual("private_research", payload["data_class"])

        self.assertEqual(1, len(repository.saved))
        saved_item, saved_chunks = repository.saved[0]
        self.assertEqual("https://example.com/research/report.pdf?a=1&b=2", saved_item.source_uri)
        self.assertEqual("manual_report", saved_item.source_type)
        self.assertEqual(DataClass.PRIVATE_RESEARCH, saved_item.data_class)
        self.assertEqual(("NVDA", "MSFT"), saved_item.tickers)
        self.assertGreaterEqual(len(saved_chunks), 1)
        self.assertTrue(all(chunk.content_hash for chunk in saved_chunks))
        self.assertTrue(all(chunk.embedding_model == "local_pending" for chunk in saved_chunks))

    def test_accepts_local_file_evidence_and_persists_manual_claims(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main
        from ai_infra_fund_core.runtime.config import RuntimeSettings

        repository = FakeEvidenceRepository()

        with TemporaryDirectory() as temp_dir:
            app = main.create_app(
                evidence_repository=repository,
                settings_provider=lambda: RuntimeSettings(
                    database_url="postgresql://user:pass@postgres:5432/db",
                    data_dir=temp_dir,
                    model_profiles_path="config/model_profiles.yaml",
                ),
            )
            report_path = Path(temp_dir) / "channel-check.md"
            report_path.write_text(
                "NVDA accelerator demand remains supply constrained through the next 12 months.\n"
                "Packaging capacity is the limiting factor cited by suppliers.",
                encoding="utf-8",
            )

            response = TestClient(app).post(
                "/internal/evidence/file",
                json={
                    "source_uri": report_path.as_uri(),
                    "source_type": "manual_report",
                    "license_label": "user_supplied_private",
                    "data_class": "private_research",
                    "title": "Supplier channel check",
                    "tickers": ["nvda"],
                    "claims": [
                        {
                            "chunk_index": 0,
                            "ticker_or_theme": "NVDA",
                            "claim_type": "supply_constraint",
                            "direction": "positive",
                            "magnitude": "0.30",
                            "time_horizon": "12m",
                            "confidence": "0.82",
                            "quote_or_span_ref": "char:0-76",
                        }
                    ],
                },
            )

        self.assertEqual(201, response.status_code)
        payload = response.json()["data"]
        self.assertEqual("private_research", payload["data_class"])
        self.assertEqual(1, payload["claim_count"])
        self.assertEqual(1, payload["chunk_count"])
        self.assertTrue(payload["local_only"])

        self.assertEqual(1, len(repository.saved_with_claims))
        saved_item, saved_chunks, saved_claims = repository.saved_with_claims[0]
        self.assertEqual("file", saved_item.source_uri.split(":", 1)[0])
        self.assertEqual(saved_item.source_uri, saved_item.storage_uri)
        self.assertEqual(DataClass.PRIVATE_RESEARCH, saved_item.data_class)
        self.assertEqual(("NVDA",), saved_item.tickers)
        self.assertEqual(1, len(saved_chunks))
        self.assertEqual(1, len(saved_claims))
        self.assertEqual(saved_item.evidence_id, saved_claims[0].evidence_id)
        self.assertEqual(saved_chunks[0].chunk_id, saved_claims[0].chunk_id)
        self.assertEqual(Decimal("0.82"), saved_claims[0].confidence)
        self.assertIsNone(saved_claims[0].extracted_by_model_run_id)

    def test_rejects_file_evidence_outside_configured_data_dir(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main
        from ai_infra_fund_core.runtime.config import RuntimeSettings

        with TemporaryDirectory() as data_dir, TemporaryDirectory() as outside_dir:
            outside_path = Path(outside_dir) / "outside.md"
            outside_path.write_text("This file is not under the configured data dir.", encoding="utf-8")
            app = main.create_app(
                evidence_repository=FakeEvidenceRepository(),
                settings_provider=lambda: RuntimeSettings(
                    database_url="postgresql://user:pass@postgres:5432/db",
                    data_dir=data_dir,
                    model_profiles_path="config/model_profiles.yaml",
                ),
            )

            response = TestClient(app).post(
                "/internal/evidence/file",
                json={
                    "source_uri": outside_path.as_uri(),
                    "source_type": "manual_report",
                    "license_label": "user_supplied_private",
                    "data_class": "private_research",
                },
            )

        self.assertEqual(422, response.status_code)
        self.assertEqual("invalid_evidence", response.json()["error"]["code"])

    def test_rejects_file_evidence_with_unsafe_or_inline_provenance(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        with TemporaryDirectory() as temp_dir:
            report_path = Path(temp_dir) / "report.md"
            report_path.write_text("Local file content.", encoding="utf-8")
            invalid_payloads = [
                {
                    "source_uri": "https://example.com/report.md",
                    "source_type": "manual_report",
                    "license_label": "public",
                    "data_class": "public_evidence",
                },
                {
                    "source_uri": report_path.as_uri(),
                    "source_type": "manual_report",
                    "license_label": "user_supplied_private",
                    "data_class": "private_research",
                    "text": "Inline text belongs on the manual endpoint.",
                },
                {
                    "source_uri": "file://remote-host/tmp/report.md",
                    "source_type": "manual_report",
                    "license_label": "user_supplied_private",
                    "data_class": "private_research",
                },
            ]

            for payload in invalid_payloads:
                with self.subTest(payload=payload):
                    repository = FakeEvidenceRepository()
                    app = main.create_app(evidence_repository=repository)

                    response = TestClient(app).post("/internal/evidence/file", json=payload)

                    self.assertEqual(422, response.status_code)
                    self.assertEqual("invalid_evidence", response.json()["error"]["code"])
                    self.assertEqual([], repository.saved)
                    self.assertEqual([], repository.saved_with_claims)

    def test_rejects_manual_evidence_missing_required_provenance(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeEvidenceRepository()
        app = main.create_app(evidence_repository=repository)

        response = TestClient(app).post(
            "/internal/evidence/manual",
            json={
                "source_type": "manual_report",
                "data_class": "private_research",
                "text": "Manual analyst note with no source URI or license.",
            },
        )

        self.assertEqual(422, response.status_code)
        self.assertEqual("invalid_evidence", response.json()["error"]["code"])
        self.assertEqual([], repository.saved)

    def test_rejects_non_manual_source_type_invalid_data_class_and_blank_text(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        invalid_payloads = [
            {
                "source_uri": "manual://research/source-1",
                "source_type": "rss_feed",
                "license_label": "public",
                "data_class": "public_evidence",
                "text": "Public source text.",
            },
            {
                "source_uri": "manual://research/source-2",
                "source_type": "manual_note",
                "license_label": "public",
                "data_class": "secrets",
                "text": "This should not be accepted as evidence.",
            },
            {
                "source_uri": "manual://research/source-3",
                "source_type": "manual_note",
                "license_label": "public",
                "data_class": "public_evidence",
                "text": "   ",
            },
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                repository = FakeEvidenceRepository()
                app = main.create_app(evidence_repository=repository)

                response = TestClient(app).post("/internal/evidence/manual", json=payload)

                self.assertEqual(422, response.status_code)
                self.assertEqual("invalid_evidence", response.json()["error"]["code"])
                self.assertEqual([], repository.saved)

    def test_api_ingestion_path_has_no_model_clients_or_execution_surface(self) -> None:
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
            API_SRC / "ai_infra_fund_api" / "routes" / "evidence.py",
            API_SRC / "ai_infra_fund_api" / "repositories" / "evidence.py",
        ]

        offenders: list[str] = []
        for path in paths:
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


class EvidenceRepositoryClaimPersistenceTests(unittest.TestCase):
    def test_persists_claims_with_evidence_and_chunk_linkage_using_parameterized_sql(self) -> None:
        from ai_infra_fund_api.repositories.evidence import EvidenceRepository
        from ai_infra_fund_core.contracts.evidence import EvidenceClaim, EvidenceItem
        from ai_infra_fund_core.evidence.chunking import EvidenceChunk

        now = datetime(2026, 5, 14, tzinfo=timezone.utc)
        item = EvidenceItem(
            evidence_id="evidence-claim-test",
            source_uri="file:///tmp/report.md",
            source_type="manual_report",
            title="Report",
            publisher=None,
            author=None,
            published_at=None,
            ingested_at=now,
            content_hash="a" * 64,
            license_label="user_supplied_private",
            data_class=DataClass.PRIVATE_RESEARCH,
            tickers=("NVDA",),
            themes=(),
            summary=None,
            storage_uri="file:///tmp/report.md",
            created_at=now,
        )
        chunk = EvidenceChunk(
            chunk_id="chunk-claim-test",
            evidence_id=item.evidence_id,
            chunk_index=0,
            chunk_text="NVDA demand remains supply constrained.",
            span_ref="char:0-39",
            content_hash="b" * 64,
            embedding_model="local_pending",
            embedding=None,
        )
        claim = EvidenceClaim(
            claim_id="claim-claim-test",
            evidence_id=item.evidence_id,
            chunk_id=chunk.chunk_id,
            ticker_or_theme="NVDA",
            claim_type="supply_constraint",
            direction="positive",
            magnitude=Decimal("0.30"),
            time_horizon="12m",
            confidence=Decimal("0.82"),
            quote_or_span_ref=chunk.span_ref,
            extracted_by_model_run_id=None,
            validated_at=None,
            created_at=now,
        )
        connection = RecordingConnection()

        returned_item, returned_chunks, returned_claims = EvidenceRepository(
            connection
        ).save_item_with_chunks_and_claims(item, (chunk,), (claim,))

        self.assertIs(item, returned_item)
        self.assertEqual((chunk,), returned_chunks)
        self.assertEqual((claim,), returned_claims)
        self.assertEqual(1, connection.commit_count)
        self.assertEqual(3, len(connection.statements))
        claim_sql, claim_params = connection.statements[-1]
        self.assertIn("INSERT INTO evidence.evidence_claims", claim_sql)
        self.assertIn("%s", claim_sql)
        self.assertNotIn("supply_constraint", claim_sql)
        self.assertEqual("claim-claim-test", claim_params[0])
        self.assertEqual(item.evidence_id, claim_params[1])
        self.assertEqual(chunk.chunk_id, claim_params[2])
        self.assertEqual("supply_constraint", claim_params[4])

    def test_rejects_claims_without_matching_evidence_or_chunk_linkage(self) -> None:
        from ai_infra_fund_api.repositories.evidence import EvidenceRepository
        from ai_infra_fund_core.contracts.evidence import EvidenceClaim, EvidenceItem
        from ai_infra_fund_core.evidence.chunking import EvidenceChunk

        now = datetime(2026, 5, 14, tzinfo=timezone.utc)
        item = EvidenceItem(
            evidence_id="evidence-claim-test",
            source_uri="file:///tmp/report.md",
            source_type="manual_report",
            title="Report",
            publisher=None,
            author=None,
            published_at=None,
            ingested_at=now,
            content_hash="a" * 64,
            license_label="user_supplied_private",
            data_class=DataClass.PRIVATE_RESEARCH,
            tickers=("NVDA",),
            themes=(),
            summary=None,
            storage_uri="file:///tmp/report.md",
            created_at=now,
        )
        chunk = EvidenceChunk(
            chunk_id="chunk-claim-test",
            evidence_id=item.evidence_id,
            chunk_index=0,
            chunk_text="NVDA demand remains supply constrained.",
            span_ref="char:0-39",
            content_hash="b" * 64,
            embedding_model="local_pending",
            embedding=None,
        )
        claim = EvidenceClaim(
            claim_id="claim-claim-test",
            evidence_id=item.evidence_id,
            chunk_id="chunk-missing",
            ticker_or_theme="NVDA",
            claim_type="supply_constraint",
            direction="positive",
            magnitude=Decimal("0.30"),
            time_horizon="12m",
            confidence=Decimal("0.82"),
            quote_or_span_ref=chunk.span_ref,
            extracted_by_model_run_id=None,
            validated_at=None,
            created_at=now,
        )

        with self.assertRaisesRegex(ValueError, "claim chunk_id must match"):
            EvidenceRepository(RecordingConnection()).save_item_with_chunks_and_claims(
                item,
                (chunk,),
                (claim,),
            )


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.saved: list[tuple[object, tuple[object, ...]]] = []
        self.saved_with_claims: list[tuple[object, tuple[object, ...], tuple[object, ...]]] = []

    def save_manual_evidence(self, item: object, chunks: tuple[object, ...]) -> object:
        self.saved.append((item, chunks))
        return item

    def save_evidence_with_claims(
        self,
        item: object,
        chunks: tuple[object, ...],
        claims: tuple[object, ...],
    ) -> object:
        self.saved_with_claims.append((item, chunks, claims))
        return item


class RecordingConnection:
    def __init__(self) -> None:
        self.statements: list[tuple[str, tuple[object, ...]]] = []
        self.commit_count = 0

    def cursor(self) -> "RecordingCursor":
        return RecordingCursor(self)

    def commit(self) -> None:
        self.commit_count += 1


class RecordingCursor:
    def __init__(self, connection: RecordingConnection) -> None:
        self._connection = connection

    def __enter__(self) -> "RecordingCursor":
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self._connection.statements.append((statement, params or ()))


if __name__ == "__main__":
    unittest.main()
