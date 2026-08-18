"""
Step 2 — Create the relational schema and load the cleaned tables into it.

Runs sql/schema.sql, bulk-loads the CSVs from data/processed/, then creates
the reusable reporting views in sql/views.sql.

Usage
-----
    python src/load.py                    # SQLite (default)
    DB_ENGINE=postgres python src/load.py # PostgreSQL
"""

from pathlib import Path

import pandas as pd
from sqlalchemy import text

from db import get_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
SQL_DIR = PROJECT_ROOT / "sql"

# Load order matters: dimensions before the fact table that references them.
LOAD_ORDER = ["dim_customer", "dim_product", "dim_location", "fact_order_lines"]


def split_statements(sql: str) -> list[str]:
    """
    Split a .sql file into executable statements.

    Comments are stripped first, then the remainder is split on ';'. Doing it
    in that order matters: splitting first would discard any statement sitting
    under a comment header, and would also break apart any statement whose
    preceding comment happens to contain a semicolon.

    Assumes no semicolons inside string literals, which holds for the .sql
    files in this repo.
    """
    without_comments = "\n".join(
        line for line in sql.splitlines() if not line.strip().startswith("--")
    )
    return [s.strip() for s in without_comments.split(";") if s.strip()]


def run_sql_file(engine, path: Path) -> None:
    """Execute a .sql file one statement at a time."""
    statements = split_statements(path.read_text(encoding="utf-8"))
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
    print(f"  ran {path.name} ({len(statements)} statements)")


def load_tables(engine) -> None:
    for name in LOAD_ORDER:
        csv_path = PROCESSED_DIR / f"{name}.csv"
        if not csv_path.exists():
            raise SystemExit(f"Missing {csv_path}. Run: python src/clean.py")

        df = pd.read_csv(csv_path)
        for col in ("order_date", "ship_date"):
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")

        df.to_sql(name, engine, if_exists="append", index=False, chunksize=5000, method="multi")
        print(f"  {name:<20} {len(df):>8,} rows loaded")


def main() -> None:
    engine = get_engine()
    print(f"Target: {engine.dialect.name}")

    print("Creating schema:")
    run_sql_file(engine, SQL_DIR / "schema.sql")

    print("Loading data:")
    load_tables(engine)

    print("Creating views:")
    run_sql_file(engine, SQL_DIR / "views.sql")

    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM fact_order_lines")).scalar_one()
    print(f"\nDone. {total:,} order lines in the database.")
    print("Next: python src/report.py")


if __name__ == "__main__":
    main()
