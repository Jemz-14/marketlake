-- Silver: daily OHLCV prices, cleaned 1:1 from bronze.
-- Casts the string trade_date to a real date, renames the OHLC columns away
-- from T-SQL reserved words ([open]/[close]), and keeps one row per
-- ticker + trade_date (latest ingest wins).
with source as (
    select * from {{ source('bronze', 'prices') }}
),

typed as (
    select
        cast(ticker as varchar(20))               as ticker,
        try_cast(trade_date as date)              as trade_date,
        [open]                                    as open_price,
        high                                      as high_price,
        low                                       as low_price,
        [close]                                   as close_price,
        adj_close                                 as adj_close_price,
        volume                                    as volume,
        try_cast(_ingested_at as datetimeoffset)  as ingested_at
    from source
    where try_cast(trade_date as date) is not null
),

deduped as (
    select *,
        row_number() over (
            partition by ticker, trade_date
            order by ingested_at desc
        ) as _rn
    from typed
)

select
    ticker,
    trade_date,
    open_price,
    high_price,
    low_price,
    close_price,
    adj_close_price,
    volume,
    ingested_at
from deduped
where _rn = 1
