-- Rangos físicos razonables para la España peninsular; fuera de ellos, el dato está mal.
select *
from {{ ref('stg_weather__hourly') }}
where temperature_c not between -25 and 50
   or precipitation_mm < 0 or precipitation_mm > 200
   or relative_humidity_pct not between 0 and 100
   or cloud_cover_pct not between 0 and 100
   or wind_speed_kmh < 0 or wind_speed_kmh > 250
