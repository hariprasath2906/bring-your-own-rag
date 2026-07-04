from __future__ import annotations

from pathlib import Path

from build_your_own_rag.config import get_settings


def run_migrations() -> None:
    try:
        import psycopg
    except Exception as exc:
        raise RuntimeError("psycopg is not installed. Install requirements or run inside the Docker app.") from exc

    schema_path = Path(__file__).with_name("schema.sql")
    schema_sql = schema_path.read_text(encoding="utf-8")
    settings = get_settings()

    with psycopg.connect(settings.dsn, autocommit=True) as conn:
        conn.execute(schema_sql)


def main() -> None:
    run_migrations()
    print("Database migrations completed.")


if __name__ == "__main__":
    main()

