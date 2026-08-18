-- ============================================================================
-- Reusable views.
--
-- These exist so recurring reports don't re-derive the same aggregation every
-- time. Power BI connects straight to them, and the ad-hoc queries in
-- analysis.sql build on top of them instead of repeating the joins.
-- ============================================================================

DROP VIEW IF EXISTS vw_monthly_sales_summary;
DROP VIEW IF EXISTS vw_order_lines_enriched;

-- The wide, joined view: fact plus every dimension attribute.
-- One place to change if the schema moves.
CREATE VIEW vw_order_lines_enriched AS
SELECT
    f.order_line_id,
    f.order_id,
    f.order_date,
    f.ship_date,
    f.ship_mode,
    c.customer_id,
    c.customer_name,
    c.segment,
    p.product_id,
    p.product_name,
    p.category,
    p.sub_category,
    l.region,
    l.state,
    l.city,
    f.sales,
    f.quantity,
    f.discount,
    f.profit
FROM fact_order_lines f
JOIN dim_customer c ON c.customer_id = f.customer_id
JOIN dim_product  p ON p.product_id  = f.product_id
JOIN dim_location l ON l.location_id = f.location_id;

-- Monthly sales summary by region and category — the recurring report.
-- SUBSTR on the date keeps this portable across SQLite and PostgreSQL.
CREATE VIEW vw_monthly_sales_summary AS
SELECT
    SUBSTR(CAST(order_date AS VARCHAR), 1, 7) AS order_month,
    region,
    category,
    COUNT(DISTINCT order_id)                  AS orders,
    SUM(quantity)                             AS units_sold,
    ROUND(SUM(sales), 2)                      AS total_sales,
    ROUND(SUM(profit), 2)                     AS total_profit,
    ROUND(AVG(discount), 4)                   AS avg_discount
FROM vw_order_lines_enriched
GROUP BY
    SUBSTR(CAST(order_date AS VARCHAR), 1, 7),
    region,
    category;
