from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
API_SRC = ROOT / "services" / "api" / "src"
WORKER_SRC = ROOT / "services" / "worker" / "src"
for path in (API_SRC, WORKER_SRC):
    sys.path.insert(0, str(path))


class WorkerJobDispatcherTests(unittest.TestCase):
    def test_worker_job_dispatcher_imports_existing_evaluation_repository(self) -> None:
        from ai_infra_fund_api.repositories.evaluation import EvaluationRepository

        source = (
            ROOT
            / "services"
            / "worker"
            / "src"
            / "ai_infra_fund_worker"
            / "jobs.py"
        ).read_text(encoding="utf-8")

        self.assertIsNotNone(EvaluationRepository)
        self.assertIn("EvaluationRepository", source)
        self.assertNotIn("EvaluationPersistenceRepository", source)


if __name__ == "__main__":
    unittest.main()
