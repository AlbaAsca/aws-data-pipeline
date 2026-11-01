"""Lambda de ingesta: tiempo horario de Open-Meteo -> Parquet en S3, particionado por fecha.

Se despliega tal cual en AWS Lambda (o en LocalStack). Solo depende de boto3, que ya
trae el runtime, y de duckdb, que va en el zip y es quien escribe el Parquet.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import duckdb

# Lista por defecto; en AWS se lee de SSM (CITIES_PARAM) para añadir ciudades sin desplegar código.
CITIES = [
    ("madrid", 40.4168, -3.7038),
    ("barcelona", 41.3874, 2.1686),
    ("valencia", 39.4699, -0.3763),
    ("sevilla", 37.3891, -5.9845),
    ("bilbao", 43.2630, -2.9350),
    ("zaragoza", 41.6488, -0.8891),
]
HOURLY = ["temperature_2m", "relative_humidity_2m", "precipitation", "wind_speed_10m", "cloud_cover"]
COLUMNS = {
    "city": "VARCHAR",
    "observed_at": "TIMESTAMP",
    "temperature_c": "DOUBLE",
    "relative_humidity_pct": "DOUBLE",
    "precipitation_mm": "DOUBLE",
    "wind_speed_kmh": "DOUBLE",
    "cloud_cover_pct": "DOUBLE",
    "ingested_at": "TIMESTAMP",
}

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
# La API de previsión solo conserva unas semanas de pasado (más atrás devuelve nulls);
# para fechas más antiguas se usa el archivo ERA5, que va con ~5 días de retraso.
FORECAST_MAX_DAYS_AGO = 30


def resolve_date(event: dict | None, today: dt.date | None = None) -> dt.date:
    """Fecha a ingerir: `event["date"]` (YYYY-MM-DD) o, por defecto, ayer en UTC."""
    today = today or dt.datetime.now(dt.UTC).date()
    if event and event.get("date"):
        day = dt.date.fromisoformat(event["date"])
        if day >= today:
            raise ValueError(f"Solo se ingieren días cerrados: {day} no es anterior a {today}")
        return day
    return today - dt.timedelta(days=1)


def load_cities(ssm_client=None) -> list[tuple[str, float, float]]:
    """Ciudades del parámetro SSM `CITIES_PARAM` (JSON [{city, lat, lon}]) o, si no hay, las de por defecto."""
    name = os.environ.get("CITIES_PARAM")
    if not name:
        return CITIES
    if ssm_client is None:
        import boto3

        ssm_client = boto3.client("ssm")
    value = json.loads(ssm_client.get_parameter(Name=name)["Parameter"]["Value"])
    return [(c["city"], float(c["lat"]), float(c["lon"])) for c in value]


def build_url(day: dt.date, today: dt.date, cities: list[tuple[str, float, float]] = CITIES) -> str:
    base = FORECAST_URL if (today - day).days <= FORECAST_MAX_DAYS_AGO else ARCHIVE_URL
    params = {
        "latitude": ",".join(str(lat) for _, lat, _ in cities),
        "longitude": ",".join(str(lon) for _, _, lon in cities),
        "hourly": ",".join(HOURLY),
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
        "timezone": "UTC",  # en UTC todos los días tienen 24 h (sin saltos de horario de verano)
        "wind_speed_unit": "kmh",
    }
    return f"{base}?{urllib.parse.urlencode(params)}"


def fetch(url: str, timeout: int = 30, retries: int = 3, backoff: float = 2.0) -> list[dict]:
    # Open-Meteo devuelve 503/429 de vez en cuando (visto en el despliegue real): se reintenta con espera.
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310 (URL fija, https)
                payload = json.load(resp)
            break
        except urllib.error.HTTPError as err:
            if err.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
            time.sleep(backoff * attempt)
    # Con varias coordenadas la API devuelve una lista; con una sola, un objeto.
    return payload if isinstance(payload, list) else [payload]


def to_rows(
    payload: list[dict], ingested_at: dt.datetime, cities: list[tuple[str, float, float]] = CITIES
) -> list[tuple]:
    if len(payload) != len(cities):
        raise ValueError(f"Se esperaban {len(cities)} ubicaciones y llegaron {len(payload)}")
    rows = []
    for (city, _, _), location in zip(cities, payload, strict=True):
        hourly = location["hourly"]
        if any(t is None for t in hourly["temperature_2m"]):
            raise ValueError(f"{city}: la API devolvió horas sin temperatura; no se escribe un día incompleto")
        for i, ts in enumerate(hourly["time"]):
            rows.append(
                (
                    city,
                    dt.datetime.fromisoformat(ts),
                    *(hourly[var][i] for var in HOURLY),
                    ingested_at,
                )
            )
    return rows


def write_parquet(rows: list[tuple], path: Path) -> None:
    con = duckdb.connect(config={"home_directory": tempfile.gettempdir()})
    try:
        con.execute(f"CREATE TABLE weather ({', '.join(f'{c} {t}' for c, t in COLUMNS.items())})")
        con.executemany(f"INSERT INTO weather VALUES ({', '.join('?' * len(COLUMNS))})", rows)
        con.execute(f"COPY weather TO '{path.as_posix()}' (FORMAT parquet, COMPRESSION zstd)")
    finally:
        con.close()


def object_key(prefix: str, day: dt.date) -> str:
    # Partición estilo Hive: la entienden igual DuckDB, Athena y Glue.
    return f"{prefix.strip('/')}/dt={day.isoformat()}/weather.parquet"


def lambda_handler(event: dict | None, context: object = None) -> dict:
    import boto3  # perezoso: el modo local sin AWS no lo necesita

    today = dt.datetime.now(dt.UTC).date()
    day = resolve_date(event, today)
    cities = load_cities()
    rows = to_rows(fetch(build_url(day, today, cities)), dt.datetime.now(dt.UTC).replace(tzinfo=None), cities)

    bucket = os.environ["RAW_BUCKET"]
    key = object_key(os.environ.get("RAW_PREFIX", "raw/weather"), day)
    with tempfile.TemporaryDirectory() as tmp:
        local = Path(tmp) / "weather.parquet"
        write_parquet(rows, local)
        # Misma clave para el mismo día: re-ejecutar es idempotente (sobrescribe).
        boto3.client("s3").upload_file(str(local), bucket, key)

    result = {"date": day.isoformat(), "rows": len(rows), "s3_uri": f"s3://{bucket}/{key}"}
    print(json.dumps(result))
    return result
