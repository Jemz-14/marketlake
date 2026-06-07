-- Silver: daily FX rates, cleaned 1:1 from bronze.
-- One row per rate_date + currency pair (latest ingest wins).
with source as (
    select * from {{ source('bronze', 'fx') }}
),

typed as (
    select
        try_cast(rate_date as date)               as rate_date,
        cast(base_currency as varchar(3))         as base_currency,
        cast(quote_currency as varchar(3))        as quote_currency,
        rate                                      as rate,
        try_cast(_ingested_at as datetimeoffset)  as ingested_at
    from source
    where try_cast(rate_date as date) is not null
),

deduped as (
    select *,
        row_number() over (
            partition by rate_date, base_currency, quote_currency
            order by ingested_at desc
        ) as _rn
    from typed
)

select
    rate_date,
    base_currency,
    quote_currency,
    rate,
    ingested_at
from deduped
where _rn = 1
