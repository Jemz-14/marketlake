-- Silver: company reference snapshot, cleaned 1:1 from bronze.
-- Collapses to the latest snapshot per ticker, so it's a clean current-state
-- dimension input for dim_security / dim_sector downstream.
with source as (
    select * from {{ source('bronze', 'fundamentals') }}
),

typed as (
    select
        cast(ticker as varchar(20))               as ticker,
        cast(long_name as varchar(255))           as company_name,
        cast(sector as varchar(100))              as sector,
        cast(industry as varchar(150))            as industry,
        market_cap                                as market_cap,
        cast(currency as varchar(3))              as currency,
        cast(exchange as varchar(30))             as exchange,
        cast(country as varchar(100))             as country,
        cast(quote_type as varchar(30))           as quote_type,
        try_cast(snapshot_date as date)           as snapshot_date,
        try_cast(_ingested_at as datetimeoffset)  as ingested_at
    from source
),

deduped as (
    select *,
        row_number() over (
            partition by ticker
            order by snapshot_date desc, ingested_at desc
        ) as _rn
    from typed
)

select
    ticker,
    company_name,
    sector,
    industry,
    market_cap,
    currency,
    exchange,
    country,
    quote_type,
    snapshot_date,
    ingested_at
from deduped
where _rn = 1
