"""Gráficas compartidas por el panel y por scripts/make_charts.py (paleta Tokyo Night)."""

import matplotlib

matplotlib.use("Agg")

import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

# Paleta Tokyo Night: https://github.com/folke/tokyonight.nvim
BG, PANEL, GRID = "#1A1B26", "#16161E", "#292E42"
FG, MUTED = "#C0CAF5", "#9AA5CE"
PALETTE = ["#7DCFFF", "#F7768E", "#E0AF68", "#9ECE6A", "#7AA2F7", "#BB9AF7"]

plt.rcParams.update(
    {
        "figure.facecolor": BG,
        "axes.facecolor": BG,
        "savefig.facecolor": BG,
        "axes.edgecolor": BG,
        "axes.labelcolor": MUTED,
        "axes.titlecolor": FG,
        "axes.grid": True,
        "grid.color": GRID,
        "grid.linewidth": 0.8,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "text.color": FG,
        "legend.labelcolor": MUTED,
        "font.size": 11,
        "axes.prop_cycle": plt.cycler(color=PALETTE),
    }
)


def _soft_glow(ax, line, color):
    """Un halo muy suave bajo cada línea: da profundidad sin el brillo neón."""
    ax.plot(
        *line.get_data(), color=color, linewidth=6, alpha=0.12, solid_capstyle="round", zorder=line.get_zorder() - 1
    )


def temperature_chart(daily: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(11, 4.5))
    lines = []
    for color, (city, df) in zip(PALETTE, daily.sort_values("observation_date").groupby("city_name"), strict=False):
        (line,) = ax.plot(df["observation_date"], df["temp_avg_c"], label=city, color=color, linewidth=2)
        _soft_glow(ax, line, color)
        lines.append(line)
    ax.set_title("Temperatura media diaria (°C)", loc="left", fontsize=14)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.legend(handles=lines, ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.12), frameon=False)
    fig.tight_layout()
    return fig


def rain_chart(summary: pd.DataFrame):
    df = summary.sort_values("precipitation_total_mm")
    fig, ax = plt.subplots(figsize=(11, 4))
    ax.barh(df["city_name"], df["precipitation_total_mm"], color=PALETTE[0], alpha=0.85, height=0.6)
    for y, (mm, days) in enumerate(zip(df["precipitation_total_mm"], df["rainy_days"], strict=True)):
        ax.text(mm, y, f"  {mm:.0f} mm · {int(days)} días de lluvia", va="center", fontsize=10, color=MUTED)
    ax.set_title("Lluvia acumulada en el periodo", loc="left", fontsize=14)
    ax.set_xlim(0, df["precipitation_total_mm"].max() * 1.3 + 1)
    ax.grid(axis="y", visible=False)
    fig.tight_layout()
    return fig
