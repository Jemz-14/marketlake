-- Gold: one row per traded security, enriched with reference attributes.
-- Built from the tickers actually present in prices (left-joined to
-- fundamentals) so the fact never references a missing security.
with tickers as (
    select distinct ticker from {{ ref('stg_prices') }}
),

fundamentals as (
    select * from {{ ref('stg_fundamentals') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['t.ticker']) }}                       as security_key,
    t.ticker,
    f.company_name,
    coalesce(f.sector, 'Unknown')                                             as sector,
    {{ dbt_utils.generate_surrogate_key(["coalesce(f.sector, 'Unknown')"]) }} as sector_key,
    f.industry,
    f.currency,
    f.exchange,
    f.country,
    f.quote_type,
    f.market_cap
from tickers t
left join fundamentals f on t.ticker = f.ticker
