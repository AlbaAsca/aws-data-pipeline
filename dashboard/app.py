"""Panel del pipeline: lee las tablas que construye dbt en data/warehouse.duckdb.

streamlit run dashboard/app.py
"""

import os
from pathlib import Path

import duckdb
import streamlit as st
from charts import rain_chart, temperature_chart

DB = Path(os.environ.get("DUCKDB_PATH", Path(__file__).resolve().parents[1] / "data" / "warehouse.duckdb"))

st.set_page_config(page_title="Tiempo en España · data pipeline", page_icon="🌦️", layout="wide")
st.title("🌦️ El tiempo en seis ciudades españolas")
st.caption("Open-Meteo → Lambda → S3 (Parquet) → dbt + DuckDB → este panel")

if not DB.exists():
    st.error(f"No encuentro {DB}. Ejecuta antes la ingesta y `dbt build` (ver README).")
    st.stop()


@st.cache_data(ttl=300)
def load(table: str):
    with duckdb.connect(str(DB), read_only=True) as con:
        return con.sql(f"select * from {table}").df()


daily, summary = load("fct_weather_daily"), load("city_climate_summary")
cities = st.multiselect("Ciudades", sorted(daily["city_name"].unique()), default=sorted(daily["city_name"].unique()))
daily, summary = daily[daily["city_name"].isin(cities)], summary[summary["city_name"].isin(cities)]
if daily.empty:
    st.stop()

first, last = daily["observation_date"].min(), daily["observation_date"].max()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Días cargados", daily["observation_date"].nunique(), f"{first:%d %b} – {last:%d %b %Y}", delta_color="off")
hottest = summary.loc[summary["temp_avg_c"].idxmax()]
c2.metric("Ciudad más cálida", hottest["city_name"], f"{hottest['temp_avg_c']} °C de media", delta_color="off")
rainiest = summary.loc[summary["precipitation_total_mm"].idxmax()]
c3.metric("Más lluviosa", rainiest["city_name"], f"{rainiest['precipitation_total_mm']:.0f} mm", delta_color="off")
windiest = summary.loc[summary["wind_record_kmh"].idxmax()]
c4.metric("Racha de viento máx.", f"{windiest['wind_record_kmh']:.0f} km/h", windiest["city_name"], delta_color="off")

st.pyplot(temperature_chart(daily))
st.pyplot(rain_chart(summary))

with st.expander("Datos diarios"):
    st.dataframe(daily.sort_values(["observation_date", "city_name"], ascending=[False, True]), hide_index=True)
