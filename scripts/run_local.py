"""Modo sin Docker: misma lógica que la Lambda, pero escribe el Parquet en data/raw/.

python scripts/run_local.py --days 60            # últimos 60 días desde Open-Meteo
python scripts/run_local.py --fixture tests/fixtures/open_meteo_2026-10-30.json --date 2026-10-30
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingest import handler  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30, help="días hacia atrás desde ayer")
    ap.add_argument("--date", help="un día concreto (YYYY-MM-DD)")
    ap.add_argument("--fixture", type=Path, help="usar un JSON guardado en vez de la API")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw")
    args = ap.parse_args()

    today = dt.datetime.now(dt.UTC).date()
    if args.date:
        days = [dt.date.fromisoformat(args.date)]
    else:
        days = [today - dt.timedelta(days=n) for n in range(args.days, 0, -1)]

    for day in days:
        payload = json.loads(args.fixture.read_text()) if args.fixture else handler.fetch(handler.build_url(day, today))
        rows = handler.to_rows(payload, ingested_at=dt.datetime.now(dt.UTC).replace(tzinfo=None))
        path = args.out / handler.object_key("weather", day)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler.write_parquet(rows, path)
        print(f"{day}  {len(rows):>4} filas  -> {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
