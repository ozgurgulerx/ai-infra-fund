from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


VALID_EVALUATION_REQUEST = {
    "backtest_run_id": "evaluation-20260514-baseline",
    "strategy_id": "strategy-baseline-weighted",
    "dataset_snapshot_ids": ["dataset-snapshot-20260514-prices"],
    "validation_protocol": "walk-forward-v1",
    "cost_assumptions": {"commission_bps": "1.0", "slippage_bps": "5.0"},
    "metrics": {
        "formula_versions": {"scores": "score-formula-v3"},
        "benchmark_version": "nasdaq-100-total-return-v2",
        "walk_forward": {"splits": 3, "mean_excess_return": "0.04"},
    },
    "artifact_hash": "a" * 64,
    "as_of": "2026-05-14T12:00:00+00:00",
    "available_at": "2026-05-14T12:30:00+00:00",
    "created_at": "2026-05-14T12:00:00+00:00",
}


class EvaluationApiTests(unittest.TestCase):
    def test_persists_precomputed_deterministic_evaluation_record(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        repository = FakeEvaluationRepository()
        app = main.create_app(evaluation_repository=repository)

        response = TestClient(app).post("/internal/evaluations", json=VALID_EVALUATION_REQUEST)

        self.assertEqual(201, response.status_code)
        payload = response.json()["data"]
        self.assertEqual("evaluation-20260514-baseline", payload["backtest_run_id"])
        self.assertEqual(["dataset-snapshot-20260514-prices"], payload["dataset_snapshot_ids"])
        self.assertEqual({"scores": "score-formula-v3"}, payload["formula_versions"])
        self.assertEqual("nasdaq-100-total-return-v2", payload["benchmark_version"])
        self.assertEqual(1, len(repository.saved_backtest_runs))

        saved_run = repository.saved_backtest_runs[0]
        self.assertEqual("strategy-baseline-weighted", saved_run.strategy_id)
        self.assertEqual(("dataset-snapshot-20260514-prices",), saved_run.dataset_snapshot_ids)
        self.assertEqual("walk-forward-v1", saved_run.validation_protocol)

    def test_rejects_generation_model_recommendation_and_order_fields(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        invalid_payloads = [
            {**VALID_EVALUATION_REQUEST, "prompt": "evaluate this strategy"},
            {**VALID_EVALUATION_REQUEST, "model_id": "configured-model"},
            {**VALID_EVALUATION_REQUEST, "target_weights": {"NVDA": "0.4"}},
            {**VALID_EVALUATION_REQUEST, "recommendation_id": "recommendation-20260514-nvda"},
            {**VALID_EVALUATION_REQUEST, "order_id": "order-123"},
            {**VALID_EVALUATION_REQUEST, "live_data_fetch": True},
        ]

        for payload in invalid_payloads:
            with self.subTest(field=set(payload) - set(VALID_EVALUATION_REQUEST)):
                repository = FakeEvaluationRepository()
                app = main.create_app(evaluation_repository=repository)

                response = TestClient(app).post("/internal/evaluations", json=payload)

                self.assertEqual(422, response.status_code)
                self.assertEqual("invalid_evaluation_request", response.json()["error"]["code"])
                self.assertEqual([], repository.saved_backtest_runs)

    def test_rejects_non_deterministic_or_incomplete_evaluation_lineage(self) -> None:
        from fastapi.testclient import TestClient

        from ai_infra_fund_api import main

        invalid_payloads = [
            {**VALID_EVALUATION_REQUEST, "backtest_run_id": "evaluation baseline"},
            {**VALID_EVALUATION_REQUEST, "dataset_snapshot_ids": []},
            {
                **VALID_EVALUATION_REQUEST,
                "metrics": {"benchmark_version": "nasdaq-100-total-return-v2"},
            },
            {
                **VALID_EVALUATION_REQUEST,
                "metrics": {"formula_versions": {"scores": "score-formula-v3"}},
            },
        ]

        for payload in invalid_payloads:
            with self.subTest(payload=payload):
                repository = FakeEvaluationRepository()
                app = main.create_app(evaluation_repository=repository)

                response = TestClient(app).post("/internal/evaluations", json=payload)

                self.assertEqual(422, response.status_code)
                self.assertEqual("invalid_evaluation_request", response.json()["error"]["code"])
                self.assertEqual([], repository.saved_backtest_runs)

    def test_evaluation_api_has_no_model_broker_or_recommendation_generation_surface(self) -> None:
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
            "execute_order",
            "create_recommendation",
            "live_data_fetch(",
        ]
        paths = [
            API_SRC / "ai_infra_fund_api" / "routes" / "evaluation.py",
            API_SRC / "ai_infra_fund_api" / "repositories" / "evaluation.py",
            API_SRC / "ai_infra_fund_api" / "main.py",
        ]

        offenders: list[str] = []
        for path in paths:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            for pattern in forbidden:
                if pattern in text:
                    offenders.append(f"{path.relative_to(ROOT)} contains {pattern}")

        self.assertEqual([], offenders)


class FakeEvaluationRepository:
    def __init__(self) -> None:
        self.saved_backtest_runs: list[object] = []

    def save_backtest_run(self, run: object) -> object:
        self.saved_backtest_runs.append(run)
        return run


if __name__ == "__main__":
    unittest.main()
