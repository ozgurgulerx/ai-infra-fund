from __future__ import annotations

from ai_infra_fund_core.runtime.config import RuntimeSettings


def check_database_connection(settings: RuntimeSettings, *, timeout_seconds: int = 3) -> bool:
    """Return true when PostgreSQL accepts a simple readiness query."""
    try:
        import psycopg
    except ModuleNotFoundError:
        return False

    try:
        with psycopg.connect(settings.database_url, connect_timeout=timeout_seconds) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return True
    except Exception:
        return False
