# Data dictionary — gold layer

The gold star schema in Azure SQL (`gold` schema), also served as Synapse
serverless views (`marketlake_serving.dbo.*`). Surrogate keys are MD5 hashes
(`dbt_utils.generate_surrogate_key`).

## fact_daily_price
**Grain:** one row per security per trade date.

| Column | Type | Description |
|---|---|---|
| `daily_price_key` | varchar | Surrogate PK — hash of (ticker, trade_date). |
| `security_key` | varchar | FK → `dim_security`. |
| `date_key` | int | FK → `dim_date` (yyyymmdd). |
| `ticker` | varchar(20) | Security symbol (e.g. `AAPL`, `BHP.AX`). |
| `trade_date` | date | Trading day. |
| `open_price` / `high_price` / `low_price` / `close_price` | float | Daily OHLC, listing currency. |
| `adj_close_price` | float | Split/dividend-adjusted close. |
| `volume` | bigint | Shares traded. |
| `currency` | varchar(3) | Listing currency of the security. |
| `aud_fx_rate` | float | AUD→currency rate used (null for AUD-listed). |
| `close_price_aud` | float | Close normalised to AUD (as-of FX join). |

## fact_price_indicators
**Grain:** one row per security per trade date.

| Column | Type | Description |
|---|---|---|
| `security_key` | varchar | FK → `dim_security`. |
| `date_key` | int | FK → `dim_date`. |
| `ticker` | varchar(20) | Security symbol. |
| `trade_date` | date | Trading day. |
| `close_price` | float | Close (listing currency), carried for context. |
| `daily_return` | float | (close − prev close) / prev close. |
| `sma_20` / `sma_50` | float | 20- / 50-day simple moving average (null during warm-up). |
| `rsi_14` | float | Relative Strength Index, 14-day (0–100). |
| `ema_12` / `ema_26` | float | Exponentially-weighted moving averages. |
| `macd_line` | float | `ema_12 − ema_26`. |
| `macd_signal` | float | EWMA(9) of the MACD line. |
| `macd_histogram` | float | `macd_line − macd_signal`. |

## dim_security
**Grain:** one row per traded security.

| Column | Type | Description |
|---|---|---|
| `security_key` | varchar | Surrogate PK — hash of ticker. |
| `ticker` | varchar(20) | Natural key. |
| `company_name` | varchar(255) | Company long name. |
| `sector` | varchar(100) | Sector (`Unknown` if absent). |
| `sector_key` | varchar | FK → `dim_sector`. |
| `industry` | varchar(150) | Industry. |
| `currency` | varchar(3) | Listing currency. |
| `exchange` | varchar(30) | Listing exchange. |
| `country` | varchar(100) | Country of listing. |
| `quote_type` | varchar(30) | Instrument type (e.g. `EQUITY`). |
| `market_cap` | bigint | Market capitalisation (listing currency). |

## dim_sector
**Grain:** one row per sector.

| Column | Type | Description |
|---|---|---|
| `sector_key` | varchar | Surrogate PK — hash of sector. |
| `sector` | varchar(100) | Sector name. |

## dim_date
**Grain:** one row per calendar day (range derived from the price history).

| Column | Type | Description |
|---|---|---|
| `date_key` | int | PK, `yyyymmdd`. |
| `full_date` | date | Calendar date. |
| `year` / `quarter` / `month` | int | Date parts. |
| `month_name` | varchar | Month name (English, CASE-mapped). |
| `day_of_month` | int | Day number. |
| `day_name` | varchar | Weekday name (DATEFIRST-independent). |
| `is_weekend` | bit | 1 for Sat/Sun, else 0. |
