-- Gold: technical indicators per security per day, computed in SQL over
-- fact_daily_price. Same grain as the fact (security x trade date).
--
--   * daily_return, sma_20, sma_50  -> window functions (LAG / windowed AVG)
--   * rsi_14                        -> Cutler's RSI: 14-period SMA of gains/losses
--   * ema_12 / ema_26 / macd        -> exponentially-weighted CROSS APPLY
--
-- EMA note: a textbook EMA is recursive (EMA_t = a*close_t + (1-a)*EMA_t-1),
-- which is awkward and recursion-capped in T-SQL. This is a finite-window
-- exponentially-weighted average: weights (1-alpha)^k over a 60-day lookback,
-- normalised by the weight sum. It converges to the textbook EMA, stays
-- set-based, and scales to any history length.
--
-- The weights are computed in an inner derived table (not in the aggregate) so
-- the SUMs reference only inner columns -- T-SQL forbids an outer reference
-- (the current row's rn) inside an aggregate alongside other columns.
{% set beta12 = 1 - 2.0 / (12 + 1) %}
{% set beta26 = 1 - 2.0 / (26 + 1) %}
{% set beta9 = 1 - 2.0 / (9 + 1) %}
{% set lookback = 60 %}

with base as (
    select
        security_key,
        date_key,
        ticker,
        trade_date,
        close_price,
        row_number() over (partition by security_key order by trade_date) as rn
    from {{ ref('fact_daily_price') }}
),

changes as (
    select
        *,
        lag(close_price) over (partition by security_key order by trade_date) as prev_close
    from base
),

gains_losses as (
    select
        *,
        case when close_price - prev_close > 0 then close_price - prev_close else 0 end as gain,
        case when close_price - prev_close < 0 then prev_close - close_price else 0 end as loss
    from changes
),

windowed as (
    select
        security_key, date_key, ticker, trade_date, close_price, rn,
        (close_price - prev_close) / nullif(prev_close, 0) as daily_return,
        case when rn >= 20
             then avg(close_price) over (partition by security_key order by trade_date
                                         rows between 19 preceding and current row) end as sma_20,
        case when rn >= 50
             then avg(close_price) over (partition by security_key order by trade_date
                                         rows between 49 preceding and current row) end as sma_50,
        case when rn >= 15
             then avg(gain) over (partition by security_key order by trade_date
                                  rows between 13 preceding and current row) end as avg_gain_14,
        case when rn >= 15
             then avg(loss) over (partition by security_key order by trade_date
                                  rows between 13 preceding and current row) end as avg_loss_14
    from gains_losses
),

ema as (
    select
        w.*,
        e.ema_12,
        e.ema_26
    from windowed w
    cross apply (
        select
            sum(cw12) / nullif(sum(wt12), 0) as ema_12,
            sum(cw26) / nullif(sum(wt26), 0) as ema_26
        from (
            select
                power(cast({{ beta12 }} as float), w.rn - b.rn)               as wt12,
                b.close_price * power(cast({{ beta12 }} as float), w.rn - b.rn) as cw12,
                power(cast({{ beta26 }} as float), w.rn - b.rn)               as wt26,
                b.close_price * power(cast({{ beta26 }} as float), w.rn - b.rn) as cw26
            from base b
            where b.security_key = w.security_key
              and b.rn between w.rn - {{ lookback - 1 }} and w.rn
        ) weights
    ) e
),

macd as (
    select
        *,
        ema_12 - ema_26 as macd_line
    from ema
)

select
    m.security_key,
    m.date_key,
    m.ticker,
    m.trade_date,
    m.close_price,
    m.daily_return,
    m.sma_20,
    m.sma_50,
    case
        when m.avg_gain_14 is null then null
        when m.avg_loss_14 = 0 then 100
        else 100 - 100 / (1 + m.avg_gain_14 / nullif(m.avg_loss_14, 0))
    end as rsi_14,
    m.ema_12,
    m.ema_26,
    m.macd_line,
    sig.macd_signal,
    m.macd_line - sig.macd_signal as macd_histogram
from macd m
cross apply (
    select sum(cw) / nullif(sum(wt), 0) as macd_signal
    from (
        select
            power(cast({{ beta9 }} as float), m.rn - m2.rn)                as wt,
            m2.macd_line * power(cast({{ beta9 }} as float), m.rn - m2.rn) as cw
        from macd m2
        where m2.security_key = m.security_key
          and m2.rn between m.rn - {{ lookback - 1 }} and m.rn
    ) weights
) sig
