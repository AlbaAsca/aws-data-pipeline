-- Cada fichero dt=YYYY-MM-DD solo puede contener horas de ese día.
select *
from {{ ref('stg_weather__hourly') }}
where cast(observed_at as date) <> observation_date
