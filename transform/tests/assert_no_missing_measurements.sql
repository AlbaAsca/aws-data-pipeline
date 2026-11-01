-- La API devuelve null en horas aún sin dato: un día cerrado no debería tener ninguno.
select *
from {{ ref('stg_weather__hourly') }}
where temperature_c is null or precipitation_mm is null
   or relative_humidity_pct is null or wind_speed_kmh is null
