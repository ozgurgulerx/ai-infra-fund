from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
CORE_SRC = ROOT / "packages" / "core" / "src"
API_SRC = ROOT / "services" / "api" / "src"
for path in (CORE_SRC, API_SRC):
    sys.path.insert(0, str(path))


class DemoChainSeedTests(unittest.TestCase):
    def test_seed_demo_chain_uses_idempotent_parameterized_inserts(self) -> None:
        from ai_infra_fund_api.seed_demo_chain import seed_demo_advisory_chain

        connection = FakeConnection()

        first = seed_demo_advisory_chain(connection)
        second = seed_demo_advisory_chain(connection)

        self.assertEqual(first, second)
        self.assertEqual("demo-ai-infra-nvda", first["chain_id"])
        self.assertEqual("recommendation-demo-nvda", first["recommendation_id"])
        self.assertEqual("advisory_only", first["advisory_label"])
        self.assertEqual(2, connection.commit_count)
        self.assertGreaterEqual(len(connection.cursor_instance.executions), 16)

        for statement, params in connection.cursor_instance.executions:
            upper_statement = statement.upper()
            self.assertIn("INSERT INTO", upper_statement)
            self.assertIn("ON CONFLICT", upper_statement)
            self.assertIsInstance(params, tuple)
            self.assertNotIn("PLACE_ORDER", upper_statement)
            self.assertNotIn("BROKER", upper_statement)
            self.assertNotIn("EXECUTION", upper_statement)

    def test_seed_script_exists_and_invokes_module_without_committing_secrets(self) -> None:
        script = ROOT / "scripts" / "seed_demo_chain.sh"

        self.assertTrue(script.is_file())
        text = script.read_text(encoding="utf-8")

        self.assertIn("ai_infra_fund_api.seed_demo_chain", text)
        self.assertNotIn("sk-", text)
        self.assertNotIn("AZURE_AI_FOUNDRY_API_KEY=", text)


class FakeCursor:
    def __init__(self) -> None:
        self.executions: list[tuple[str, tuple[object, ...]]] = []

    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        self.executions.append((statement, params if params is not None else ()))

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


if __name__ == "__main__":
    unittest.main()
