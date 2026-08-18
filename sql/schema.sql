-- ============================================================================
-- Relational schema — star layout: three dimensions, one fact table.
--
-- The raw CSV is a single wide, denormalized file. Splitting it this way
-- removes repeated customer/product/location text from every order line,
-- keeps updates in one place, and gives the analysis queries real joins to
-- work with. Written to run on both SQLite and PostgreSQL.
-- ============================================================================

DROP TABLE IF EXISTS fact_order_lines;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS dim_product;
DROP TABLE IF EXISTS dim_location;

-- ---------------------------------------------------------------- dimensions

CREATE TABLE dim_customer (
    customer_id   VARCHAR(32)  PRIMARY KEY,
    customer_name VARCHAR(120),
    segment       VARCHAR(40)
);

CREATE TABLE dim_product (
    product_id   VARCHAR(32)  PRIMARY KEY,
    product_name VARCHAR(255),
    category     VARCHAR(60),
    sub_category VARCHAR(60)
);

CREATE TABLE dim_location (
    location_id INTEGER      PRIMARY KEY,
    country     VARCHAR(60),
    region      VARCHAR(40),
    state       VARCHAR(60),
    city        VARCHAR(80),
    postal_code VARCHAR(20)
);

-- ---------------------------------------------------------------------- fact

CREATE TABLE fact_order_lines (
    order_line_id INTEGER      PRIMARY KEY,
    order_id      VARCHAR(40)  NOT NULL,
    order_date    DATE         NOT NULL,
    ship_date     DATE,
    ship_mode     VARCHAR(40),
    customer_id   VARCHAR(32)  REFERENCES dim_customer (customer_id),
    product_id    VARCHAR(32)  REFERENCES dim_product (product_id),
    location_id   INTEGER      REFERENCES dim_location (location_id),
    sales         NUMERIC(12, 2) NOT NULL,
    quantity      INTEGER        NOT NULL,
    discount      NUMERIC(5, 4),
    profit        NUMERIC(12, 2)
);

-- ------------------------------------------------------------------- indexes
-- The dashboard filters and groups on date, region, and category constantly,
-- so index the foreign keys and the date column those filters land on.

CREATE INDEX idx_fact_order_date  ON fact_order_lines (order_date);
CREATE INDEX idx_fact_customer    ON fact_order_lines (customer_id);
CREATE INDEX idx_fact_product     ON fact_order_lines (product_id);
CREATE INDEX idx_fact_location    ON fact_order_lines (location_id);
CREATE INDEX idx_product_category ON dim_product (category, sub_category);
CREATE INDEX idx_location_region  ON dim_location (region);
