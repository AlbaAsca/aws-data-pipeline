-- Una fila por ciudad para todo el periodo cargado.
select
    city,
    city_name,
    region,
    min(observation_date) as first_day,
    max(observation_date) as last_day,
    count(*) as days_observed,
    round(avg(temp_avg_c), 1) as temp_avg_c,
    max(temp_max_c) as temp_record_max_c,
    min(temp_min_c) as temp_record_min_c,
    round(sum(precipitation_mm), 1) as precipitation_total_mm,
    count_if(is_rainy_day) as rainy_days,
    max(wind_max_kmh) as wind_record_kmh
from {{ ref('fct_weather_daily') }}
group by all
