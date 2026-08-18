"""Local Streamlit dashboard for the retail sales project."""

from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

st.set_page_config(page_title="Retail Sales Performance", page_icon="📊", layout="wide")


@st.cache_data
def demo_data() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    dates = pd.date_range("2024-01-01", "2024-12-31", periods=240)
    regions = np.array(["West", "East", "Central", "South"])
    categories = np.array(["Technology", "Furniture", "Office Supplies"])
    products = np.array(["Laptop", "Monitor", "Desk", "Chair", "Paper", "Binder"])
    discounts = rng.choice([0, 0.05, 0.10, 0.20, 0.30], 240, p=[.22, .24, .22, .20, .12])
    sales = rng.uniform(80, 1600, 240).round(2)
    profit = (sales * rng.uniform(.04, .28, 240) - sales * discounts * .55).round(2)
    return pd.DataFrame({
        "order_date": dates,
        "region": rng.choice(regions, 240),
        "category": rng.choice(categories, 240),
        "product_name": rng.choice(products, 240),
        "customer_id": [f"C{i:04d}" for i in rng.integers(1, 81, 240)],
        "sales": sales,
        "profit": profit,
        "quantity": rng.integers(1, 8, 240),
        "discount": discounts,
    })


@st.cache_data
def load_data() -> tuple[pd.DataFrame, bool]:
    fact_path = PROCESSED_DIR / "fact_order_lines.csv"
    if not fact_path.exists():
        return demo_data(), True

    fact = pd.read_csv(fact_path, parse_dates=["order_date"])
    products = pd.read_csv(PROCESSED_DIR / "dim_product.csv")
    locations = pd.read_csv(PROCESSED_DIR / "dim_location.csv")
    customers = pd.read_csv(PROCESSED_DIR / "dim_customer.csv")
    data = fact.merge(products, on="product_id", how="left")
    data = data.merge(locations, on="location_id", how="left")
    data = data.merge(customers[["customer_id", "customer_name"]], on="customer_id", how="left")
    return data, False


def money(value: float) -> str:
    return f"${value:,.0f}"


data, using_demo = load_data()
data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
data["margin"] = data["profit"] / data["sales"].replace(0, np.nan)

st.title("Retail Sales Performance")
st.caption("Sales, profitability, and customer concentration in one view")
if using_demo:
    st.info("Showing clearly labeled demo data. Add a CSV to data/raw/ and run the pipeline to show your results.")
else:
    st.success("Showing your processed dataset.")

with st.sidebar:
    st.header("Filters")
    regions = sorted(data["region"].dropna().unique())
    selected_regions = st.multiselect("Region", regions, default=regions)
    categories = sorted(data["category"].dropna().unique())
    selected_categories = st.multiselect("Category", categories, default=categories)
    min_date = data["order_date"].min().date()
    max_date = data["order_date"].max().date()
    selected_dates = st.date_input("Order date", (min_date, max_date), min_value=min_date, max_value=max_date)

filtered = data[data["region"].isin(selected_regions) & data["category"].isin(selected_categories)].copy()
if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
    filtered = filtered[filtered["order_date"].dt.date.between(selected_dates[0], selected_dates[1])]

sales = filtered["sales"].sum()
profit = filtered["profit"].sum()
orders = filtered.get("order_id", pd.Series(filtered.index)).nunique()
margin = profit / sales if sales else 0
kpis = st.columns(4)
kpis[0].metric("Total sales", money(sales))
kpis[1].metric("Total profit", money(profit))
kpis[2].metric("Profit margin", f"{margin:.1%}")
kpis[3].metric("Orders", f"{orders:,}")

left, right = st.columns(2)
with left:
    st.subheader("Monthly sales")
    monthly = filtered.set_index("order_date")["sales"].resample("MS").sum()
    st.line_chart(monthly)
with right:
    st.subheader("Sales by region")
    by_region = filtered.groupby("region")["sales"].sum().sort_values(ascending=False)
    st.bar_chart(by_region)

left, right = st.columns(2)
with left:
    st.subheader("Top products by revenue")
    top_products = filtered.groupby("product_name")["sales"].sum().nlargest(10).sort_values()
    st.bar_chart(top_products)
with right:
    st.subheader("Discount vs. margin")
    bands = pd.cut(filtered["discount"].fillna(0), [-.01, 0, .10, .20, .30, 1], labels=["0%", "1-10%", "11-20%", "21-30%", "30%+"])
    discount_view = filtered.assign(discount_band=bands).groupby("discount_band", observed=False).agg(sales=("sales", "sum"), profit=("profit", "sum"))
    discount_view["margin"] = discount_view["profit"] / discount_view["sales"].replace(0, np.nan)
    st.bar_chart(discount_view["margin"].dropna().mul(100))

st.subheader("Customer revenue concentration")
customer_sales = filtered.groupby("customer_id")["sales"].sum().sort_values(ascending=False)
customer_share = customer_sales.cumsum() / customer_sales.sum() if customer_sales.sum() else customer_sales
st.line_chart(customer_share.rename("Cumulative revenue share"))
