-- ============================================================================
-- Analysis queries.
--
-- Each block answers one business question. Read the comment above each one
-- before you run it — you will be asked to explain these in an interview, and
-- "the script generated it" is not an answer.
-- ============================================================================


-- ----------------------------------------------------------------------------
-- Q1. Regional sales trend with a running total.
--
-- The CTE aggregates to one row per region per month, and the window function
-- then accumulates over that result. Doing it in one pass without the CTE would
-- mean mixing an aggregate and a window over raw rows, which reads badly and
-- recomputes the grouping for every row.
-- ----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        region,
        SUBSTR(CAST(order_date AS VARCHAR), 1, 7) AS order_month,
        SUM(sales)  AS monthly_sales,
        SUM(profit) AS monthly_profit
    FROM vw_order_lines_enriched
    GROUP BY region, SUBSTR(CAST(order_date AS VARCHAR), 1, 7)
)
SELECT
    region,
    order_month,
    ROUND(monthly_sales, 2) AS monthly_sales,
    ROUND(SUM(monthly_sales) OVER (
        PARTITION BY region
        ORDER BY order_month
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS running_sales,
    ROUND(monthly_profit, 2) AS monthly_profit
FROM monthly
ORDER BY region, order_month;


-- ----------------------------------------------------------------------------
-- Q2. Top 5 products in each category by revenue.
--
-- DENSE_RANK rather than ROW_NUMBER: genuine ties should share a rank instead
-- of being separated arbitrarily. The rank has to be computed in a CTE because
-- window functions can't appear in a WHERE clause — they're evaluated after it.
-- ----------------------------------------------------------------------------
WITH product_revenue AS (
    SELECT
        category,
        product_id,
        product_name,
        SUM(sales)  AS total_sales,
        SUM(profit) AS total_profit,
        SUM(quantity) AS units_sold
    FROM vw_order_lines_enriched
    GROUP BY category, product_id, product_name
),
ranked AS (
    SELECT
        *,
        DENSE_RANK() OVER (PARTITION BY category ORDER BY total_sales DESC) AS revenue_rank
    FROM product_revenue
)
SELECT
    category,
    revenue_rank,
    product_name,
    ROUND(total_sales, 2)  AS total_sales,
    ROUND(total_profit, 2) AS total_profit,
    units_sold
FROM ranked
WHERE revenue_rank <= 5
ORDER BY category, revenue_rank;


-- ----------------------------------------------------------------------------
-- Q3. Month-over-month growth by category.
--
-- LAG pulls the previous month's value onto the current row so the change can
-- be computed without a self-join. NULLIF guards the first month of each
-- category, where the lagged value is NULL and the divisor would be zero.
-- ----------------------------------------------------------------------------
WITH monthly AS (
    SELECT
        category,
        SUBSTR(CAST(order_date AS VARCHAR), 1, 7) AS order_month,
        SUM(sales) AS monthly_sales
    FROM vw_order_lines_enriched
    GROUP BY category, SUBSTR(CAST(order_date AS VARCHAR), 1, 7)
)
SELECT
    category,
    order_month,
    ROUND(monthly_sales, 2) AS monthly_sales,
    ROUND(LAG(monthly_sales) OVER (PARTITION BY category ORDER BY order_month), 2)
        AS prev_month_sales,
    ROUND(
        100.0 * (monthly_sales - LAG(monthly_sales) OVER (PARTITION BY category ORDER BY order_month))
        / NULLIF(LAG(monthly_sales) OVER (PARTITION BY category ORDER BY order_month), 0),
        2
    ) AS mom_growth_pct
FROM monthly
ORDER BY category, order_month;


-- ----------------------------------------------------------------------------
-- Q4. Does discounting destroy margin?
--
-- This is the headline question. Bucket every order line by discount depth,
-- then compare profit margin across buckets. Read the output before you write
-- anything about it on a resume — the shape of the answer depends on the
-- dataset, and on some of them the effect is weak or absent.
-- ----------------------------------------------------------------------------
WITH banded AS (
    SELECT
        CASE
            WHEN discount = 0            THEN '0%'
            WHEN discount <= 0.10        THEN '1-10%'
            WHEN discount <= 0.20        THEN '11-20%'
            WHEN discount <= 0.30        THEN '21-30%'
            ELSE '30%+'
        END AS discount_band,
        sales,
        profit,
        order_id
    FROM vw_order_lines_enriched
    WHERE discount IS NOT NULL
)
SELECT
    discount_band,
    COUNT(*)                  AS order_lines,
    COUNT(DISTINCT order_id)  AS orders,
    ROUND(SUM(sales), 2)      AS total_sales,
    ROUND(SUM(profit), 2)     AS total_profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS profit_margin_pct
FROM banded
GROUP BY discount_band
ORDER BY discount_band;


-- ----------------------------------------------------------------------------
-- Q5. Customer value deciles.
--
-- NTILE(10) splits customers into ten equal-sized buckets by lifetime spend.
-- Useful for showing how concentrated revenue is — usually far more than
-- people expect.
-- ----------------------------------------------------------------------------
WITH customer_totals AS (
    SELECT
        customer_id,
        customer_name,
        segment,
        SUM(sales)               AS lifetime_sales,
        COUNT(DISTINCT order_id) AS orders
    FROM vw_order_lines_enriched
    GROUP BY customer_id, customer_name, segment
),
deciled AS (
    SELECT
        *,
        NTILE(10) OVER (ORDER BY lifetime_sales DESC) AS spend_decile
    FROM customer_totals
)
SELECT
    spend_decile,
    COUNT(*)                        AS customers,
    ROUND(SUM(lifetime_sales), 2)   AS decile_sales,
    ROUND(AVG(lifetime_sales), 2)   AS avg_customer_value,
    ROUND(100.0 * SUM(lifetime_sales) / SUM(SUM(lifetime_sales)) OVER (), 2)
        AS pct_of_total_sales
FROM deciled
GROUP BY spend_decile
ORDER BY spend_decile;


-- ----------------------------------------------------------------------------
-- Q6. Loss-making sub-categories by region.
--
-- A plain join and aggregate, but it's the query that tends to produce the
-- most actionable finding: the specific region/sub-category pairs that sell
-- well and still lose money.
-- ----------------------------------------------------------------------------
SELECT
    region,
    sub_category,
    ROUND(SUM(sales), 2)  AS total_sales,
    ROUND(SUM(profit), 2) AS total_profit,
    ROUND(100.0 * SUM(profit) / NULLIF(SUM(sales), 0), 2) AS margin_pct,
    ROUND(AVG(discount), 3) AS avg_discount
FROM vw_order_lines_enriched
GROUP BY region, sub_category
HAVING SUM(profit) < 0
ORDER BY SUM(profit) ASC;
