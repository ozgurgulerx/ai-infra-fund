from __future__ import annotations

from pathlib import Path
import sys
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


class FakeEvidenceRepository:
    def __init__(self) -> None:
        self.saved: list[tuple[object, tuple[object, ...]]] = []

    def save_manual_evidence(self, item: object, chunks: tuple[object, ...]) -> object:
        self.saved.append((item, chunks))
        return item


if __name__ == "__main__":
    unittest.main()
