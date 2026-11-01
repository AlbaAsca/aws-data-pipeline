-- Una fila por ciudad y hora (UTC). Si un día se re-ingiere, gana la última carga.
with source as (
    select *
    from read_parquet('{{ var("raw_glob") }}', hive_partitioning = true, union_by_name = true)
),

deduplicated as (
    select
        *,
        row_number() over (partition by city, observed_at order by ingested_at desc) as load_rank
    from source
)

select
    city,
    observed_at,
    cast(dt as date) as observation_date,
    temperature_c,
    relative_humidity_pct,
    precipitation_mm,
    wind_speed_kmh,
    cloud_cover_pct,
    ingested_at
from deduplicated
where load_rank = 1
