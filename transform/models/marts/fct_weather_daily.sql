-- Resumen diario por ciudad: la tabla que consume el panel.
select
    h.city,
    c.city_name,
    c.region,
    h.observation_date,
    count(*) as hours_observed,
    round(min(h.temperature_c), 1) as temp_min_c,
    round(max(h.temperature_c), 1) as temp_max_c,
    round(avg(h.temperature_c), 1) as temp_avg_c,
    round(sum(h.precipitation_mm), 1) as precipitation_mm,
    sum(h.precipitation_mm) >= 1 as is_rainy_day,
    round(max(h.wind_speed_kmh), 1) as wind_max_kmh,
    round(avg(h.relative_humidity_pct), 0) as humidity_avg_pct,
    round(avg(h.cloud_cover_pct), 0) as cloud_cover_avg_pct
from {{ ref('stg_weather__hourly') }} as h
inner join {{ ref('cities') }} as c using (city)
group by all
