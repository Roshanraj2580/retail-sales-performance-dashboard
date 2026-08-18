"""
Step 1 — Clean and normalize the raw retail CSV.

Reads data/raw/*.csv, standardizes column names and types, handles missing
values and duplicates, then splits the flat file into normalized tables:

    dim_customer, dim_product, dim_location, fact_order_lines

Output goes to data/processed/ as CSVs, which load.py then writes to the DB.

Usage
-----
    python src/clean.py
    python src/clean.py --input data/raw/superstore.csv
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Maps the many spellings these public datasets use onto one canonical name.
COLUMN_ALIASES = {
    "row_id": "row_id",
    "order_id": "order_id",
    "order_date": "order_date",
    "ship_date": "ship_date",
    "ship_mode": "ship_mode",
    "customer_id": "customer_id",
    "customer_name": "customer_name",
    "segment": "segment",
    "country": "country",
    "city": "city",
    "state": "state",
    "postal_code": "postal_code",
    "region": "region",
    "product_id": "product_id",
    "category": "category",
    "sub_category": "sub_category",
    "subcategory": "sub_category",
    "product_name": "product_name",
    "sales": "sales",
    "sale_price": "sales",
    "quantity": "quantity",
    "discount": "discount",
    "discount_percent": "discount",
    "profit": "profit",
    "cost_price": "cost_price",
    "list_price": "list_price",
}

MISSING_TOKENS = ["Not Available", "not available", "unknown", "Unknown", "N/A", "NA", ""]


def find_input_file(explicit: str | None) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            sys.exit(f"Input file not found: {path}")
        return path

    candidates = sorted(RAW_DIR.glob("*.csv"))
    if not candidates:
        sys.exit(
            f"No CSV found in {RAW_DIR}.\n"
            "Download a retail dataset first — see README.md, 'Get the data'."
        )
    if len(candidates) > 1:
        print(f"Multiple CSVs found; using {candidates[0].name}. "
              f"Pass --input to choose another.")
    return candidates[0]


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Lowercase, underscore, and map column names onto canonical ones."""
    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[ \-]+", "_", regex=True)
        .str.replace(r"[^\w]", "", regex=True)
    )
    df = df.rename(columns={c: COLUMN_ALIASES[c] for c in df.columns if c in COLUMN_ALIASES})
    return df


def coerce_types(df: pd.DataFrame) -> pd.DataFrame:
    for col in ("order_date", "ship_date"):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=False)

    for col in ("sales", "quantity", "discount", "profit", "cost_price", "list_price"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    if "postal_code" in df.columns:
        df["postal_code"] = df["postal_code"].astype("string").str.strip()

    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype("string").str.strip()

    return df


def derive_missing_measures(df: pd.DataFrame) -> pd.DataFrame:
    """
    Some retail datasets ship cost_price / list_price / discount_percent instead
    of sales / profit. Derive the measures we need when they're absent.
    """
    if "discount" in df.columns and df["discount"].max(skipna=True) is not pd.NA:
        # Normalize percentages expressed as 0-100 down to 0-1.
        if df["discount"].max(skipna=True) > 1:
            df["discount"] = df["discount"] / 100.0

    if "sales" not in df.columns and {"list_price", "quantity"} <= set(df.columns):
        discount = df["discount"].fillna(0) if "discount" in df.columns else 0
        df["sales"] = df["list_price"] * (1 - discount) * df["quantity"]

    if "profit" not in df.columns and {"cost_price", "quantity"} <= set(df.columns):
        df["profit"] = df["sales"] - (df["cost_price"] * df["quantity"])

    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    df = df.replace(MISSING_TOKENS, pd.NA)
    df = standardize_columns(df)
    df = coerce_types(df)
    df = derive_missing_measures(df)

    df = df.drop_duplicates()
    deduped = before - len(df)

    required = ["order_id", "order_date", "product_id", "sales", "quantity"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        sys.exit(
            f"Dataset is missing required columns: {missing_cols}\n"
            f"Columns found: {sorted(df.columns)}\n"
            "Add the mapping to COLUMN_ALIASES at the top of this file."
        )

    dropped = df[required].isna().any(axis=1).sum()
    df = df.dropna(subset=required)

    # Synthesize the keys the schema needs if the dataset doesn't carry them.
    if "customer_id" not in df.columns:
        source = "customer_name" if "customer_name" in df.columns else "order_id"
        df["customer_id"] = "C" + df[source].factorize()[0].astype(str).str.zfill(6)
    if "customer_name" not in df.columns:
        df["customer_name"] = pd.NA
    for col in ("segment", "country", "state", "city", "postal_code", "region",
                "product_name", "category", "sub_category", "ship_mode", "profit"):
        if col not in df.columns:
            df[col] = pd.NA

    df["order_line_id"] = range(1, len(df) + 1)

    print(f"  rows in           : {before:,}")
    print(f"  exact duplicates  : {deduped:,}")
    print(f"  incomplete rows   : {dropped:,}")
    print(f"  rows out          : {len(df):,}")
    return df


def build_dimensions(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    dim_customer = (
        df[["customer_id", "customer_name", "segment"]]
        .drop_duplicates(subset="customer_id")
        .sort_values("customer_id")
        .reset_index(drop=True)
    )

    dim_product = (
        df[["product_id", "product_name", "category", "sub_category"]]
        .drop_duplicates(subset="product_id")
        .sort_values("product_id")
        .reset_index(drop=True)
    )

    location_cols = ["country", "region", "state", "city", "postal_code"]
    dim_location = (
        df[location_cols]
        .drop_duplicates()
        .sort_values(location_cols)
        .reset_index(drop=True)
    )
    dim_location.insert(0, "location_id", range(1, len(dim_location) + 1))

    fact = df.merge(dim_location, on=location_cols, how="left")[
        [
            "order_line_id", "order_id", "order_date", "ship_date", "ship_mode",
            "customer_id", "product_id", "location_id",
            "sales", "quantity", "discount", "profit",
        ]
    ]

    return {
        "dim_customer": dim_customer,
        "dim_product": dim_product,
        "dim_location": dim_location,
        "fact_order_lines": fact,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean and normalize retail sales data.")
    parser.add_argument("--input", help="Path to the raw CSV (defaults to first file in data/raw/)")
    args = parser.parse_args()

    src = find_input_file(args.input)
    print(f"Reading {src.name}")
    df = pd.read_csv(src, encoding="utf-8", encoding_errors="replace", low_memory=False)

    print("Cleaning:")
    df = clean(df)

    print("Normalizing into dimension and fact tables:")
    tables = build_dimensions(df)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        out = PROCESSED_DIR / f"{name}.csv"
        table.to_csv(out, index=False)
        print(f"  {name:<20} {len(table):>8,} rows  ->  {out.relative_to(PROJECT_ROOT)}")

    print("\nDone. Next: python src/load.py")


if __name__ == "__main__":
    main()
