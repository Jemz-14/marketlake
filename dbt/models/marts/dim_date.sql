-- Gold: calendar date dimension. Covers a fixed range that spans the price
-- history; widen the bounds here if the data ever extends beyond them.
--
-- Built with a SQL Server-friendly numbers spine: dbt_utils.date_spine emits an
-- ORDER BY inside a CTE, which T-SQL rejects. row_number()'s ordering lives in
-- the OVER() clause (allowed) and TOP bounds the row count.
{% set start_date = "2024-01-01" %}
{% set end_date = "2028-01-01" %}

with numbers as (
    select top (datediff(day, cast('{{ start_date }}' as date), cast('{{ end_date }}' as date)))
        row_number() over (order by (select null)) - 1 as n
    from sys.all_objects a
    cross join sys.all_objects b
),

dates as (
    select dateadd(day, n, cast('{{ start_date }}' as date)) as date_day
    from numbers
)

select
    cast(convert(varchar(8), date_day, 112) as int)  as date_key,
    cast(date_day as date)                            as full_date,
    year(date_day)                                    as [year],
    datepart(quarter, date_day)                       as [quarter],
    month(date_day)                                   as [month],
    datename(month, date_day)                         as month_name,
    day(date_day)                                     as day_of_month,
    datename(weekday, date_day)                       as day_name,
    case when datename(weekday, date_day) in ('Saturday', 'Sunday')
         then 1 else 0 end                            as is_weekend
from dates
