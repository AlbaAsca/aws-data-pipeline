select city, observation_date, count(*) as n
from {{ ref('fct_weather_daily') }}
group by all
having count(*) > 1
