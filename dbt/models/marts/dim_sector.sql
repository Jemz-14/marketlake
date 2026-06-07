-- Gold: distinct sectors. Derived from dim_security so every security's
-- sector_key is guaranteed to resolve here (referential integrity by design).
with sectors as (
    select distinct sector from {{ ref('dim_security') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['sector']) }} as sector_key,
    sector
from sectors
