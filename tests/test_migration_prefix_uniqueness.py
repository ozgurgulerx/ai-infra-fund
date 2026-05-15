from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS_DIR = ROOT / "services" / "api" / "migrations"
PREFIX_RE = re.compile(r"^(\d{4})_")


class MigrationPrefixUniquenessTests(unittest.TestCase):
    def test_every_migration_has_a_unique_numeric_prefix(self) -> None:
        prefixes: dict[str, list[str]] = {}
        for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
            match = PREFIX_RE.match(migration.name)
            self.assertIsNotNone(
                match,
                f"migration {migration.name} must start with a 4-digit prefix",
            )
            assert match is not None
            prefixes.setdefault(match.group(1), []).append(migration.name)

        collisions = {
            prefix: names for prefix, names in prefixes.items() if len(names) > 1
        }
        self.assertFalse(
            collisions,
            f"migration prefixes must be unique; got collisions: {collisions}",
        )


if __name__ == "__main__":
    unittest.main()
