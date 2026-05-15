from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))

from fastapi.testclient import TestClient  # noqa: E402

from ai_infra_fund_api import main  # noqa: E402


class FakeCrawlActivityRepository:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.calls = 0

    def get_crawl_activity_summary(self) -> dict[str, object]:
        self.calls += 1
        return self._payload


class CrawlActivityRouteTests(unittest.TestCase):
    def test_returns_data_envelope_with_repository_payload(self) -> None:
        payload = {
            "total": 18,
            "succeeded": 12,
            "not_modified": 3,
            "client_error": 1,
            "server_error": 0,
            "failed": 2,
            "window_hours": 24,
        }
        repo = FakeCrawlActivityRepository(payload)

        app = main.create_app(
            connection_check=lambda _settings: True,
            crawl_activity_repository=repo,
        )
        response = TestClient(app).get("/internal/dashboard/crawl-activity")

        self.assertEqual(200, response.status_code)
        self.assertEqual({"data": payload}, response.json())
        self.assertEqual(1, repo.calls)

    def test_returns_503_when_repository_unavailable(self) -> None:
        class FailingRepo:
            def get_crawl_activity_summary(self) -> dict[str, object]:
                from ai_infra_fund_api.routes.crawl import (
                    CrawlActivityRepositoryUnavailable,
                )

                raise CrawlActivityRepositoryUnavailable("not configured")

        app = main.create_app(
            connection_check=lambda _settings: True,
            crawl_activity_repository=FailingRepo(),
        )
        response = TestClient(app).get("/internal/dashboard/crawl-activity")
        self.assertEqual(503, response.status_code)
        body = response.json()
        self.assertEqual("crawl_activity_unavailable", body["error"]["code"])


if __name__ == "__main__":
    unittest.main()
