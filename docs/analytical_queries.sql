/* ============================================================================
   MarketLake — analytical queries over the gold star schema.

   These run against the Synapse SERVERLESS serving database `marketlake_serving`
   (the dbo.* OPENROWSET views over the gold Parquet), and unchanged against the
   Azure SQL `gold` schema. They demonstrate CTEs, window functions, and joins
   across the star schema.
   ============================================================================ */

-- 1) Top 3 single-day gains per security.
--    RANK() over each ticker's daily returns.
with ranked as (
    select
        ticker,
        trade_date,
        daily_return,
        rank() over (partition by ticker order by daily_return desc) as rnk
    from dbo.fact_price_indicators
    where daily_return is not null
)
select ticker, trade_date, round(daily_return * 100, 2) as pct_gain
from ranked
where rnk <= 3
order by ticker, rnk;


-- 2) Bullish crossover signals: the close crossing above its 20-day SMA.
--    LAG() compares each day to the previous to detect the cross.
with c as (
    select
        ticker,
        trade_date,
        close_price,
        sma_20,
        lag(close_price) over (partition by ticker order by trade_date) as prev_close,
        lag(sma_20)      over (partition by ticker order by trade_date) as prev_sma_20
    from dbo.fact_price_indicators
    where sma_20 is not null
)
select ticker, trade_date as signal_date,
       round(close_price, 2) as close_price, round(sma_20, 2) as sma_20
from c
where prev_close <= prev_sma_20 and close_price > sma_20
order by ticker, signal_date;


-- 3) Sector performance: average per-security total AUD return over the period.
--    FIRST_VALUE/LAST_VALUE pick each security's first & last AUD close, then we
--    roll up to the sector via the dimension joins.
with per_security as (
    select
        f.security_key,
        s.sector,
        first_value(f.close_price_aud) over (
            partition by f.security_key order by f.trade_date
            rows between unbounded preceding and unbounded following) as first_aud,
        last_value(f.close_price_aud) over (
            partition by f.security_key order by f.trade_date
            rows between unbounded preceding and unbounded following) as last_aud
    from dbo.fact_daily_price f
    join dbo.dim_security s on f.security_key = s.security_key
),
returns as (
    select distinct security_key, sector, (last_aud - first_aud) / first_aud as total_return
    from per_security
)
select sector,
       count(*) as securities,
       round(avg(total_return) * 100, 2) as avg_return_pct
from returns
group by sector
order by avg_return_pct desc;


-- 4) Per-security period summary: total AUD return and annualised volatility.
--    STDEVP (population) of daily returns annualised by sqrt(252), matching the
--    Power BI measure. Endpoints via window funcs.
with daily as (
    select
        f.ticker, s.sector, f.trade_date, f.close_price_aud, i.daily_return
    from dbo.fact_daily_price f
    join dbo.dim_security s on f.security_key = s.security_key
    join dbo.fact_price_indicators i
        on f.security_key = i.security_key and f.date_key = i.date_key
),
agg as (
    select ticker, sector, count(*) as trading_days, stdevp(daily_return) as daily_vol
    from daily
    group by ticker, sector
),
endpoints as (
    select distinct
        ticker,
        first_value(close_price_aud) over (partition by ticker order by trade_date
            rows between unbounded preceding and unbounded following) as first_aud,
        last_value(close_price_aud) over (partition by ticker order by trade_date
            rows between unbounded preceding and unbounded following) as last_aud
    from daily
)
select a.ticker, a.sector, a.trading_days,
       round((e.last_aud - e.first_aud) / e.first_aud * 100, 2) as total_return_pct,
       round(a.daily_vol * sqrt(252.0) * 100, 2) as annualised_vol_pct
from agg a
join endpoints e on a.ticker = e.ticker
order by total_return_pct desc;
