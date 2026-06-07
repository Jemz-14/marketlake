-- Gold: calendar date dimension.
--
-- Bounds are DERIVED from the loaded data (whole years spanning the price
-- history, plus the following year as headroom) and the table is rebuilt each
-- run, so it always covers every fact trade_date -- no hard-coded range to
-- outgrow.
--
-- Built with a SQL Server-friendly numbers spine: dbt_utils.date_spine emits an
-- ORDER BY inside a CTE, which T-SQL rejects. row_number()'s ordering lives in
-- the OVER() clause (allowed) and TOP bounds the row count.
--
-- Weekday/weekend are computed via an ISO day-of-week formula that is
-- independent of @@DATEFIRST and the session language (datename(weekday) would
-- be both); month/day names use explicit CASE maps for the same reason.

with bounds as (
    select
        datefromparts(year(min(trade_date)), 1, 1)       as start_date,
        datefromparts(year(max(trade_date)) + 1, 12, 31) as end_date
    from {{ ref('stg_prices') }}
),

numbers as (
    select top (select datediff(day, start_date, end_date) + 1 from bounds)
        row_number() over (order by (select null)) - 1 as n
    from sys.all_objects a
    cross join sys.all_objects b
),

calendar as (
    select
        dateadd(day, num.n, b.start_date) as date_day,
        -- ISO weekday: 1 = Monday ... 7 = Sunday, independent of @@DATEFIRST.
        (datepart(weekday, dateadd(day, num.n, b.start_date)) + @@datefirst + 5) % 7 + 1 as iso_dow
    from numbers num
    cross join bounds b
)

select
    cast(convert(varchar(8), date_day, 112) as int)  as date_key,
    cast(date_day as date)                            as full_date,
    year(date_day)                                    as [year],
    datepart(quarter, date_day)                       as [quarter],
    month(date_day)                                   as [month],
    case month(date_day)
        when 1 then 'January'  when 2 then 'February'  when 3 then 'March'
        when 4 then 'April'    when 5 then 'May'       when 6 then 'June'
        when 7 then 'July'     when 8 then 'August'    when 9 then 'September'
        when 10 then 'October' when 11 then 'November' when 12 then 'December'
    end                                               as month_name,
    day(date_day)                                     as day_of_month,
    case iso_dow
        when 1 then 'Monday'    when 2 then 'Tuesday'  when 3 then 'Wednesday'
        when 4 then 'Thursday'  when 5 then 'Friday'   when 6 then 'Saturday'
        when 7 then 'Sunday'
    end                                               as day_name,
    case when iso_dow in (6, 7) then 1 else 0 end     as is_weekend
from calendar
