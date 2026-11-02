"""GIF animado para el README: 60 días de temperatura dibujándose (docs/img/temperature.gif)."""

import sys
from pathlib import Path

import duckdb
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))

from charts import PALETTE  # noqa: E402  (también aplica el estilo Tokyo Night)


def main() -> None:
    with duckdb.connect(str(ROOT / "data" / "warehouse.duckdb"), read_only=True) as con:
        daily = con.sql("select city_name, observation_date, temp_avg_c from fct_weather_daily").df()
    daily = daily.sort_values("observation_date")
    days = sorted(daily["observation_date"].unique())
    series = {c: df for c, df in daily.groupby("city_name")}

    fig, ax = plt.subplots(figsize=(10, 4.2), dpi=90)
    ax.set_xlim(days[0], days[-1])
    ax.set_ylim(daily["temp_avg_c"].min() - 2, daily["temp_avg_c"].max() + 2)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_title("Temperatura media diaria (°C) · 6 ciudades", loc="left", fontsize=14)
    lines, glows, dots = {}, {}, {}
    for color, city in zip(PALETTE, series, strict=False):
        glows[city] = ax.plot([], [], color=color, linewidth=7, alpha=0.12)[0]
        lines[city] = ax.plot([], [], color=color, linewidth=2, label=city)[0]
        dots[city] = ax.plot([], [], "o", color=color, markersize=6)[0]
    ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.1), frameon=False, fontsize=9)
    label = ax.text(0.99, 0.95, "", transform=ax.transAxes, ha="right", va="top", fontsize=12, color="#7DCFFF")
    fig.tight_layout()

    def draw(i: int):
        # El fotograma 0 es el gráfico completo: es el que se ve si el GIF está en pausa.
        until = days[-1] if i == 0 else days[min(i - 1, len(days) - 1)]
        for city, df in series.items():
            part = df[df["observation_date"] <= until]
            for artist in (lines[city], glows[city]):
                artist.set_data(part["observation_date"], part["temp_avg_c"])
            dots[city].set_data(part["observation_date"].tail(1), part["temp_avg_c"].tail(1))
        label.set_text(f"{until:%d %b %Y}")
        return [*lines.values(), *glows.values(), *dots.values(), label]

    frames = len(days) + 16  # pausa al final antes de repetir
    anim = FuncAnimation(fig, draw, frames=frames, interval=80, blit=True)
    out = ROOT / "docs" / "img" / "temperature.gif"
    anim.save(out, writer=PillowWriter(fps=12))
    print(f"{out.relative_to(ROOT)}  ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
