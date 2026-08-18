# Retail Sales Performance Dashboard

End-to-end retail analytics pipeline: raw CSV → Pandas cleaning → normalized
relational schema → SQL analysis → Power BI dashboard.

**Stack:** Python (Pandas), SQL (SQLite / PostgreSQL), Power BI

---

## What this does

A raw retail export arrives as one wide, denormalized CSV with duplicated
customer and product text on every row. This project:

1. **Cleans it** — standardizes column names and types, resolves the several
   spellings of "missing", drops exact duplicates and incomplete rows.
2. **Normalizes it** — splits the flat file into three dimension tables and one
   fact table, with primary keys, foreign keys, and indexes on the columns the
   dashboard actually filters by.
3. **Analyzes it** — six SQL queries using joins, CTEs, and window functions
   (`SUM OVER`, `DENSE_RANK`, `LAG`, `NTILE`) to answer questions about
   regional trends, product ranking, month-over-month growth, discount
   economics, and customer concentration.
4. **Reports it** — two reusable views that Power BI connects to directly, so
   recurring reports don't re-derive the same aggregation each time.

---

## Repository layout

```
├── src/
│   ├── db.py          Connection helper (SQLite or PostgreSQL, env-driven)
│   ├── clean.py       Step 1 — clean and normalize the raw CSV
│   ├── load.py        Step 2 — build the schema and load the tables
│   └── report.py      Step 3 — print the headline numbers from your own data
├── sql/
│   ├── schema.sql     Tables, keys, indexes
│   ├── views.sql      vw_order_lines_enriched, vw_monthly_sales_summary
│   └── analysis.sql   Six analysis queries, each with its reasoning
├── powerbi/
│   └── README.md      How to build the dashboard on top of the views
├── docs/
│   └── FINDINGS.md    Your results — fill this in after your run
└── data/              Gitignored; datasets are never committed
```

---

## Get the data

This repo ships no dataset. Download one of these into `data/raw/`:

| Dataset | Where | Notes |
|---|---|---|
| Sample Superstore | Kaggle: `vivek468/superstore-dataset-final` | ~10k rows, has `Sales`, `Profit`, `Discount` directly. Easiest start. |
| Retail Orders | Kaggle: `ankitbansal06/retail-orders` | Ships `cost_price` / `list_price` / `discount_percent`; the cleaner derives `sales` and `profit` from them. |

Any retail CSV with order, product, and customer columns will work —
`COLUMN_ALIASES` at the top of `src/clean.py` maps the naming variants, and you
can add your own.

---

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python src/clean.py     # data/raw/*.csv  ->  data/processed/*.csv
python src/load.py      # builds schema, loads tables, creates views
python src/report.py    # prints your actual numbers
```

Defaults to SQLite with no setup. For PostgreSQL:

```bash
cp .env.example .env    # fill in your credentials
export DB_ENGINE=postgres DB_NAME=retail DB_USER=postgres DB_PASSWORD=...
python src/load.py
```

Then open `sql/analysis.sql` in your SQL client and work through the queries.

---

## Schema

```
dim_customer ──┐
dim_product  ──┼──< fact_order_lines
dim_location ──┘
```

`fact_order_lines` holds one row per product per order, with the measures
(`sales`, `quantity`, `discount`, `profit`) and foreign keys out to the three
dimensions. Star layout rather than full third normal form: it keeps the joins
shallow, which is what a BI tool wants.

---

## A note on the numbers

Every figure in `docs/FINDINGS.md` should come from your own run of
`src/report.py`, not from an example. The discount and margin relationship in
particular varies a lot between datasets — check what yours actually shows
before you describe it anywhere.
