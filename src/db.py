"""
Database connection helper.

Works with either SQLite (zero setup, good for a first run) or PostgreSQL
(what you'd use in a real analytics stack). Controlled by environment
variables so no credentials are ever committed.

Environment variables
---------------------
DB_ENGINE   'sqlite' (default) or 'postgres'
DB_HOST     PostgreSQL host        (default: localhost)
DB_PORT     PostgreSQL port        (default: 5432)
DB_NAME     database name          (default: retail)
DB_USER     PostgreSQL user        (default: postgres)
DB_PASSWORD PostgreSQL password
SQLITE_PATH path to .db file       (default: data/retail.db)
"""

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def get_engine() -> Engine:
    """Return a SQLAlchemy engine for the configured database."""
    engine_kind = os.getenv("DB_ENGINE", "sqlite").lower()

    if engine_kind == "postgres":
        host = os.getenv("DB_HOST", "localhost")
        port = os.getenv("DB_PORT", "5432")
        name = os.getenv("DB_NAME", "retail")
        user = os.getenv("DB_USER", "postgres")
        password = os.getenv("DB_PASSWORD", "")
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"
        return create_engine(url, future=True)

    if engine_kind == "sqlite":
        sqlite_path = os.getenv("SQLITE_PATH", str(PROJECT_ROOT / "data" / "retail.db"))
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(f"sqlite:///{sqlite_path}", future=True)

    raise ValueError(f"Unsupported DB_ENGINE: {engine_kind!r}. Use 'sqlite' or 'postgres'.")


def dialect_name() -> str:
    """'sqlite' or 'postgresql' — used where SQL syntax differs slightly."""
    return get_engine().dialect.name
