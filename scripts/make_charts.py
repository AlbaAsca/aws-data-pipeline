"""Regenera las gráficas del README (docs/img/) desde data/warehouse.duckdb."""

import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from charts import rain_chart, temperature_chart  # noqa: E402


def main() -> None:
    with duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True) as con:
        daily = con.sql("select * from fct_weather_daily").df()
        summary = con.sql("select * from city_climate_summary").df()
    out = ROOT / "docs" / "img"
    out.mkdir(parents=True, exist_ok=True)
    temperature_chart(daily).savefig(out / "temperature.png", dpi=150)
    rain_chart(summary).savefig(out / "rain.png", dpi=150)
    print(f"Gráficas en {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
