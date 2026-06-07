-- Gold: the fact table. Grain = one row per security per trade date.
-- Carries OHLCV plus an AUD-normalised close: each price is divided by the
-- AUD->listing-currency rate, picked as-of (most recent rate on/before the
-- trade date) so weekend/holiday gaps in the FX feed don't produce nulls.
with prices as (
    select * from {{ ref('stg_prices') }}
),

securities as (
    select ticker, currency from {{ ref('dim_security') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['p.ticker', 'p.trade_date']) }} as daily_price_key,
    {{ dbt_utils.generate_surrogate_key(['p.ticker']) }}                 as security_key,
    cast(convert(varchar(8), p.trade_date, 112) as int)                 as date_key,
    p.ticker,
    p.trade_date,
    p.open_price,
    p.high_price,
    p.low_price,
    p.close_price,
    p.adj_close_price,
    p.volume,
    s.currency,
    fx.rate                                                             as aud_fx_rate,
    case
        when s.currency = 'AUD'    then p.close_price
        when fx.rate is not null   then p.close_price / fx.rate
    end                                                                 as close_price_aud
from prices p
left join securities s on p.ticker = s.ticker
outer apply (
    select top 1 f.rate
    from {{ ref('stg_fx') }} f
    where f.quote_currency = s.currency
      and f.rate_date <= p.trade_date
    order by f.rate_date desc
) fx
