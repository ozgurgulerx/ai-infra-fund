from __future__ import annotations

import sys
import unittest
from unittest.mock import patch
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


VALID_BODY = {
    "strategy_id": "strategy-ai-infra-v1",
    "dataset_snapshot_ids": ["dataset-snapshot-2026q1"],
    "validation_protocol": "walk_forward_v1",
    "cost_assumptions": {"spread_bps": "5"},
    "pipeline_inputs": {"placeholder": True},
    "formula_version": "v1",
    "model_run_id": "model-run-shadow-001",
    "git_sha": "abc1234",
    "as_of": "2026-04-01T12:00:00+00:00",
}


class FakeBacktestRequestService:
    def __init__(self) -> None:
        self.enqueued: list[dict[str, object]] = []
        self.responses: dict[str, dict[str, object]] = {}

    def enqueue(self, payload: dict[str, object]) -> dict[str, object]:
        self.enqueued.append(payload)
        request_id = "backtest-req-fixed-001"
        record = {
            "request_id": request_id,
            "status": "queued",
            "strategy_id": payload["strategy_id"],
        }
        self.responses[request_id] = record
        return record

    def get(self, request_id: str) -> dict[str, object] | None:
        return self.responses.get(request_id)

    def list_recent(self, *, limit: int = 50) -> list[dict[str, object]]:
        return list(self.responses.values())[-limit:]


class BacktestApiTests(unittest.TestCase):
    def test_create_backtest_returns_201_with_request_id(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(main.create_app(backtest_request_service=service))

        response = client.post("/internal/backtests", json=VALID_BODY)

        self.assertEqual(201, response.status_code)
        body = response.json()
        self.assertEqual("queued", body["data"]["status"])
        self.assertTrue(body["data"]["request_id"].startswith("backtest-req-"))
        self.assertEqual(1, len(service.enqueued))
        self.assertEqual("strategy-ai-infra-v1", service.enqueued[0]["strategy_id"])

    def test_create_backtest_rejects_missing_required_fields(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(main.create_app(backtest_request_service=service))

        bad_body = {
            key: value for key, value in VALID_BODY.items() if key != "strategy_id"
        }
        response = client.post("/internal/backtests", json=bad_body)

        self.assertEqual(422, response.status_code)
        self.assertEqual(0, len(service.enqueued))

    def test_get_backtest_returns_status(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(main.create_app(backtest_request_service=service))
        client.post("/internal/backtests", json=VALID_BODY)

        response = client.get("/internal/backtests/backtest-req-fixed-001")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertEqual("queued", body["data"]["status"])

    def test_get_backtest_returns_404_when_missing(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(main.create_app(backtest_request_service=service))

        response = client.get("/internal/backtests/backtest-req-missing")

        self.assertEqual(404, response.status_code)

    def test_list_recent_returns_envelope(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(main.create_app(backtest_request_service=service))
        client.post("/internal/backtests", json=VALID_BODY)

        response = client.get("/internal/backtests/recent")

        self.assertEqual(200, response.status_code)
        body = response.json()
        self.assertIn("data", body)
        self.assertEqual(1, body["data"]["count"])

    def test_internal_route_rejects_request_without_token_when_configured(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(
            main.create_app(
                backtest_request_service=service,
                internal_token="secret-token",
            )
        )

        response = client.post("/internal/backtests", json=VALID_BODY)

        self.assertEqual(401, response.status_code)
        self.assertEqual([], service.enqueued)

    def test_internal_route_accepts_request_with_matching_token(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(
            main.create_app(
                backtest_request_service=service,
                internal_token="secret-token",
            )
        )

        response = client.post(
            "/internal/backtests",
            json=VALID_BODY,
            headers={"X-Internal-Token": "secret-token"},
        )

        self.assertEqual(201, response.status_code)
        self.assertEqual(1, len(service.enqueued))

    def test_production_app_refuses_to_start_without_internal_token(self) -> None:
        from ai_infra_fund_api import main

        with patch.dict(
            "os.environ",
            {
                "AI_INFRA_FUND_ENV": "production",
                "AI_INFRA_FUND_DATABASE_URL": "postgresql://example",
                "AI_INFRA_FUND_DATA_DIR": "/tmp/data",
                "AI_INFRA_FUND_MODEL_PROFILES": "config/model_profiles.yaml",
            },
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "AI_INFRA_FUND_INTERNAL_TOKEN"):
                main.create_app(backtest_request_service=FakeBacktestRequestService())

    def test_create_backtest_rejects_oversize_pipeline_inputs(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        service = FakeBacktestRequestService()
        client = TestClient(main.create_app(backtest_request_service=service))

        oversize_body = dict(VALID_BODY)
        oversize_body["pipeline_inputs"] = {"blob": "x" * (1_100_000)}

        response = client.post("/internal/backtests", json=oversize_body)

        self.assertEqual(413, response.status_code)
        self.assertEqual([], service.enqueued)


if __name__ == "__main__":
    unittest.main()
