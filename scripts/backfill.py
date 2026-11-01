"""Invoca la Lambda desplegada una vez por día (LocalStack o AWS real).

AWS_ENDPOINT_URL=http://localhost:4566 python scripts/backfill.py --days 30
"""

import argparse
import datetime as dt
import json

import boto3


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--function", default="weather-pipeline-dev-ingest")
    args = ap.parse_args()

    client = boto3.client("lambda")
    today = dt.datetime.now(dt.UTC).date()
    for n in range(args.days, 0, -1):
        day = (today - dt.timedelta(days=n)).isoformat()
        resp = client.invoke(FunctionName=args.function, Payload=json.dumps({"date": day}))
        body = json.loads(resp["Payload"].read())
        if resp.get("FunctionError"):
            raise SystemExit(f"{day}: la Lambda falló -> {body}")
        print(f"{day}  {body['rows']:>4} filas  -> {body['s3_uri']}")


if __name__ == "__main__":
    main()
