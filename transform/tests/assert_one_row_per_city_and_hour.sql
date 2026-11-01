select city, observed_at, count(*) as n
from {{ ref('stg_weather__hourly') }}
group by all
having count(*) > 1
