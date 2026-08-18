"""
Step 3 — Print the real numbers from your own run.

Everything this prints comes from your database, not from an assumption.
Copy these into docs/FINDINGS.md and into your resume bullets so the figures
you quote are ones you can defend.

Usage
-----
    python src/report.py
"""

import pandas as pd
from sqlalchemy import text

from db import get_engine

pd.set_option("display.width", 100)
pd.set_option("display.max_columns", 20)


def q(engine, sql: str) -> pd.DataFrame:
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def main() -> None:
    engine = get_engine()

    print("=" * 72)
    print("SCALE")
    print("=" * 72)
    counts = q(engine, """
        SELECT
            (SELECT COUNT(*) FROM fact_order_lines)            AS order_lines,
            (SELECT COUNT(DISTINCT order_id) FROM fact_order_lines) AS orders,
            (SELECT COUNT(*) FROM dim_customer)                AS customers,
            (SELECT COUNT(*) FROM dim_product)                 AS products,
            (SELECT COUNT(*) FROM dim_location)                AS locations
    """)
    for col in counts.columns:
        print(f"  {col:<14} {counts[col].iloc[0]:>10,}")

    span = q(engine, """
        SELECT MIN(order_date) AS first_order, MAX(order_date) AS last_order
        FROM fact_order_lines
    """)
    print(f"  date range     {span['first_order'].iloc[0]}  to  {span['last_order'].iloc[0]}")

    print()
    print("=" * 72)
    print("DISCOUNT vs MARGIN   (the discounting question)")
    print("=" * 72)
    bands = q(engine, """
        WITH banded AS (
            SELECT
                CASE
                    WHEN discount = 0     THEN '0%'
                    WHEN discount <= 0.10 THEN '1-10%'
                    WHEN discount <= 0.20 THEN '11-20%'
                    WHEN discount <= 0.30 THEN '21-30%'
                    ELSE '30%+'
                END AS discount_band,
                sales, profit
            FROM vw_order_lines_enriched
            WHERE discount IS NOT NULL
        )
        SELECT
            discount_band,
            COUNT(*)              AS order_lines,
            ROUND(SUM(sales), 2)  AS total_sales,
            ROUND(SUM(profit), 2) AS total_profit,
            ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct
        FROM banded
        GROUP BY discount_band
        ORDER BY discount_band
    """)
    print(bands.to_string(index=False))

    try:
        low = bands.loc[bands["discount_band"].isin(["0%", "1-10%"]), "margin_pct"].mean()
        high = bands.loc[bands["discount_band"].isin(["21-30%", "30%+"]), "margin_pct"].mean()
        print(f"\n  margin at 0-10% discount : {low:.2f}%")
        print(f"  margin at 21%+ discount  : {high:.2f}%")
        print(f"  difference               : {low - high:.2f} percentage points")
        print("\n  ^ This is the number to quote. Describe it as a margin gap in")
        print("    percentage points, not as a percent drop — they aren't the same.")
    except Exception:
        print("\n  (Not enough discount variation in this dataset to compare bands.)")

    print()
    print("=" * 72)
    print("TOP REGIONS")
    print("=" * 72)
    print(q(engine, """
        SELECT region,
               ROUND(SUM(sales), 2)  AS total_sales,
               ROUND(SUM(profit), 2) AS total_profit,
               ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct
        FROM vw_order_lines_enriched
        GROUP BY region
        ORDER BY SUM(sales) DESC
    """).to_string(index=False))

    print()
    print("=" * 72)
    print("LOSS-MAKING SUB-CATEGORIES")
    print("=" * 72)
    losses = q(engine, """
        SELECT region, sub_category,
               ROUND(SUM(sales), 2)  AS total_sales,
               ROUND(SUM(profit), 2) AS total_profit
        FROM vw_order_lines_enriched
        GROUP BY region, sub_category
        HAVING SUM(profit) < 0
        ORDER BY SUM(profit) ASC
    """)
    print(losses.head(10).to_string(index=False) if len(losses)
          else "  None — every region/sub-category pair is profitable.")

    print()
    print("=" * 72)
    print("REVENUE CONCENTRATION")
    print("=" * 72)
    top_decile = q(engine, """
        WITH customer_totals AS (
            SELECT customer_id, SUM(sales) AS lifetime_sales
            FROM vw_order_lines_enriched
            GROUP BY customer_id
        ),
        deciled AS (
            SELECT *, NTILE(10) OVER (ORDER BY lifetime_sales DESC) AS spend_decile
            FROM customer_totals
        )
        SELECT ROUND(100.0 * SUM(CASE WHEN spend_decile = 1 THEN lifetime_sales ELSE 0 END)
                     / NULLIF(SUM(lifetime_sales), 0), 2) AS top_decile_share_pct
        FROM deciled
    """)
    print(f"  Top 10% of customers account for "
          f"{top_decile['top_decile_share_pct'].iloc[0]}% of revenue.")

    print()
    print("Write these into docs/FINDINGS.md before you touch your resume.")


if __name__ == "__main__":
    main()
