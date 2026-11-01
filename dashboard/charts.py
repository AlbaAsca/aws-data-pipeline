"""Gráficas compartidas por el panel y por scripts/make_charts.py (estilo mplcyberpunk)."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import mplcyberpunk  # noqa: E402, F401  (registra el estilo "cyberpunk")
import pandas as pd  # noqa: E402

plt.style.use("cyberpunk")
PALETTE = ["#08F7FE", "#FE53BB", "#F5D300", "#00ff41", "#FF6C11", "#9467FD"]


def temperature_chart(daily: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 4.5))
    lines = []
    for color, (city, df) in zip(PALETTE, daily.sort_values("observation_date").groupby("city_name"), strict=False):
        lines += ax.plot(df["observation_date"], df["temp_avg_c"], label=city, color=color, linewidth=2)
    mplcyberpunk.make_lines_glow(ax)  # añade copias difuminadas: la leyenda usa solo las originales
    ax.set_title("Temperatura media diaria (°C)", loc="left", fontsize=14)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(handles=lines, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    fig.tight_layout()
    return fig


def rain_chart(summary: pd.DataFrame):
    df = summary.sort_values("precipitation_total_mm")
    fig, ax = plt.subplots(figsize=(11, 4))
    bars = ax.barh(df["city_name"], df["precipitation_total_mm"], color=PALETTE[0])
    mplcyberpunk.add_bar_gradient(bars=bars)
    for y, (mm, days) in enumerate(zip(df["precipitation_total_mm"], df["rainy_days"], strict=True)):
        ax.text(mm, y, f"  {mm:.0f} mm · {int(days)} días de lluvia", va="center", fontsize=10)
    ax.set_title("Lluvia acumulada en el periodo", loc="left", fontsize=14)
    ax.set_xlim(0, df["precipitation_total_mm"].max() * 1.3 + 1)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig
