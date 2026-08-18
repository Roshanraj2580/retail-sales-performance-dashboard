# Power BI dashboard

The `.pbix` file isn't in this repo — build it yourself, both because Power BI
files are large binaries that don't diff usefully, and because you'll need to
be able to explain every visual on it.

## Connect

**PostgreSQL:** Get Data → PostgreSQL database → host `localhost`, database
`retail`. Import `vw_order_lines_enriched` and `vw_monthly_sales_summary`.

**SQLite:** Power BI has no native SQLite connector. Either point it at the CSVs
in `data/processed/`, or install the SQLite ODBC driver and connect through
Get Data → ODBC.

Connect to the **views**, not the raw tables — the joins are already done, and
if the schema changes you fix it in one place.

## Suggested visuals

Eight is a reasonable target: enough to tell a story, few enough that each one
earns its place.

| # | Visual | Shows |
|---|---|---|
| 1 | KPI cards | Total sales, total profit, margin %, order count |
| 2 | Line chart | Monthly sales, one line per region |
| 3 | Line chart | Running total of sales over time |
| 4 | Bar chart | Top 10 products by revenue, sliced by category |
| 5 | Clustered column | Profit margin % by discount band ← the headline finding |
| 6 | Map | Sales by state |
| 7 | Matrix | Region × sub-category, profit conditionally formatted so losses go red |
| 8 | Bar chart | Revenue share by customer decile |

Slicers for date range, region, and category, applied across the page.

## Useful DAX

```dax
Total Sales   = SUM(vw_order_lines_enriched[sales])
Total Profit  = SUM(vw_order_lines_enriched[profit])
Profit Margin = DIVIDE([Total Profit], [Total Sales])

Sales YTD     = TOTALYTD([Total Sales], 'Date'[Date])

Sales MoM %   =
VAR Current  = [Total Sales]
VAR Previous = CALCULATE([Total Sales], DATEADD('Date'[Date], -1, MONTH))
RETURN DIVIDE(Current - Previous, Previous)
```

`TOTALYTD` and `DATEADD` need a proper date table marked as such — create one
with `CALENDARAUTO()` and set Table tools → Mark as date table.

## Before you call it done

Export a screenshot of the finished dashboard to `powerbi/dashboard.png` and
reference it in the main README. A recruiter who won't install Power BI will
still look at an image.
