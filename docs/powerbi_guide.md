# Power BI dashboard — build guide

The gold layer is already a clean **star schema**, which Power BI models
natively. This guide gets you from a blank report to a portfolio dashboard.
You author the `.pbix` in **Power BI Desktop** (free); the connection, model,
visuals, and measures are below.

You can connect to **either** serving surface — they expose the same tables:

| Surface | Server | Database |
|---|---|---|
| Synapse serverless (recommended — the Phase 3 serving layer) | `synmarketlakedev7f82-ondemand.sql.azuresynapse.net` | `marketlake_serving` |
| Azure SQL gold (direct) | `sql-marketlake-dev-7f82.database.windows.net` | `marketlake` (schema `gold`) |

## 1. Connect

1. **Home → Get data → Azure → Azure Synapse Analytics SQL** (for Azure SQL gold, choose **Azure SQL database**).
2. Server = the value above; Database = the value above.
3. **Data Connectivity mode: Import** (the dataset is tiny — Import is fast and enables all DAX).
4. Auth:
   - **Database** (SQL login): user `synapseadmin` / password from `cd infra; terraform output -raw synapse_admin_password`. Simplest.
   - or **Microsoft account** (Azure AD) if you prefer SSO.
5. In the Navigator, tick the five views/tables: `dim_date`, `dim_security`,
   `dim_sector`, `fact_daily_price`, `fact_price_indicators` → **Load**.

## 2. Model (Model view)

Create these relationships (single-direction, one-to-many from dim → fact):

```
dim_date[date_key]        1 → *  fact_daily_price[date_key]
dim_security[security_key] 1 → * fact_daily_price[security_key]
dim_date[date_key]        1 → *  fact_price_indicators[date_key]
dim_security[security_key] 1 → * fact_price_indicators[security_key]
dim_sector[sector_key]    1 → *  dim_security[sector_key]
```

Then select `dim_date` → **Table tools → Mark as date table** (date column = `full_date`).

## 3. Measures

**Create each measure separately** — click **New measure**, paste **one** block
below (the `Name =` prefix sets the measure name), press Enter, then repeat.
Do NOT paste all of them into one measure. Create `First Close AUD` and
`Last Close AUD` before `Period Return %` (it references them).

```dax
First Close AUD =
CALCULATE ( SUM ( fact_daily_price[close_price_aud] ),
    FIRSTNONBLANK ( fact_daily_price[trade_date], 1 ) )

Last Close AUD =
CALCULATE ( SUM ( fact_daily_price[close_price_aud] ),
    LASTNONBLANK ( fact_daily_price[trade_date], 1 ) )

Period Return % =
DIVIDE ( [Last Close AUD] - [First Close AUD], [First Close AUD] )

Avg Daily Return = AVERAGE ( fact_price_indicators[daily_return] )

Annualised Volatility % =
STDEV.P ( fact_price_indicators[daily_return] ) * SQRT ( 252 )

Latest RSI =
CALCULATE ( AVERAGE ( fact_price_indicators[rsi_14] ),
    LASTNONBLANK ( fact_price_indicators[trade_date], 1 ) )

Total Market Cap = SUM ( dim_security[market_cap] )
```

Format `Period Return %` and `Annualised Volatility %` as Percentage.

## 4. Suggested report pages / visuals

**Page 1 — Portfolio performance**
- Line chart: Axis `dim_date[full_date]`, Values `fact_daily_price[close_price_aud]`, Legend `dim_security[ticker]`.
- KPI cards: `Period Return %`, `Annualised Volatility %`, `Last Close AUD`.
- Slicers: `dim_security[ticker]`, `dim_date[full_date]` (between), `dim_sector[sector]`.

**Page 2 — Technical indicators** (single ticker via slicer)
- Line chart: `close_price`, `sma_20`, `sma_50`, `ema_12`, `ema_26` over `full_date`.
- Line/area: `rsi_14` over `full_date` (add constant lines at 70 / 30).
- Clustered column: `macd_histogram` over `full_date`, plus `macd_line` / `macd_signal` lines.

**Page 3 — Sector & returns**
- Treemap or bar: `Total Market Cap` (or `Period Return %`) by `dim_sector[sector]`.
- Table: ticker, sector, `Period Return %`, `Annualised Volatility %`, `Latest RSI`.

## 5. Save & capture
Save as `docs/marketlake_dashboard.pbix` and screenshot a page to
`docs/images/dashboard.png` to embed in the README.

> The Synapse serverless endpoint is pay-per-query; Import mode means Power BI
> only queries on refresh, so cost stays in pennies.
