from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Iterable, Protocol

from ai_infra_fund_core.runtime.config import RuntimeConfigError, RuntimeSettings


MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "migrations"


@dataclass(frozen=True)
class Migration:
    name: str
    sql: str


class Cursor(Protocol):
    def execute(self, statement: str, params: tuple[object, ...] | None = None) -> None:
        ...

    def fetchone(self) -> tuple[object, ...] | None:
        ...


class Connection(Protocol):
    def cursor(self) -> object:
        ...

    def commit(self) -> None:
        ...


def load_migrations(migrations_dir: Path = MIGRATIONS_DIR) -> list[Migration]:
    return [
        Migration(path.name, path.read_text(encoding="utf-8"))
        for path in sorted(migrations_dir.glob("*.sql"))
    ]


def ensure_migration_table(connection: Connection) -> None:
    with connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS audit;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS audit.schema_migrations (
                migration_name TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """
        )
    connection.commit()


def has_migration(connection: Connection, migration_name: str) -> bool:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT EXISTS (SELECT 1 FROM audit.schema_migrations WHERE migration_name = %s);",
            (migration_name,),
        )
        row = cursor.fetchone()
    return bool(row and row[0])


def apply_migrations(connection: Connection, migrations: Iterable[Migration]) -> list[str]:
    ensure_migration_table(connection)
    applied: list[str] = []

    for migration in sorted(migrations, key=lambda item: item.name):
        if has_migration(connection, migration.name):
            continue
        with connection.cursor() as cursor:
            cursor.execute(migration.sql)
            cursor.execute(
                "INSERT INTO audit.schema_migrations (migration_name) VALUES (%s);",
                (migration.name,),
            )
        connection.commit()
        applied.append(migration.name)

    return applied


def open_connection(settings: RuntimeSettings) -> Connection:
    try:
        import psycopg
    except ModuleNotFoundError as error:
        raise RuntimeError("psycopg is required to run migrations") from error

    return psycopg.connect(settings.database_url, autocommit=False)


def main() -> None:
    try:
        settings = RuntimeSettings.from_env(os.environ, allow_defaults=False)
        migrations = load_migrations()
        if not migrations:
            raise RuntimeError(f"No SQL migrations found under {MIGRATIONS_DIR}")

        with open_connection(settings) as connection:
            applied = apply_migrations(connection, migrations)
    except (RuntimeConfigError, RuntimeError) as error:
        print(f"migration failed: {error}", file=sys.stderr)
        raise SystemExit(2) from error

    if applied:
        print(f"Applied migrations: {', '.join(applied)}")
    else:
        print("No migrations pending.")


if __name__ == "__main__":
    main()
