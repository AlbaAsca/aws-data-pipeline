import datetime as dt
import json
from pathlib import Path

import boto3
import duckdb
import pytest
from moto import mock_aws

from ingest import handler

FIXTURE = Path(__file__).parent / "fixtures" / "open_meteo_2026-10-30.json"
TODAY = dt.date(2026, 11, 1)


@pytest.fixture
def payload():
    return json.loads(FIXTURE.read_text())


def test_resolve_date_defaults_to_yesterday():
    assert handler.resolve_date({}, TODAY) == dt.date(2026, 10, 31)


def test_resolve_date_rejects_today_and_future():
    with pytest.raises(ValueError):
        handler.resolve_date({"date": "2026-11-01"}, TODAY)


def test_build_url_switches_to_archive_for_old_dates():
    assert handler.build_url(dt.date(2026, 10, 30), TODAY).startswith(handler.FORECAST_URL)
    assert handler.build_url(dt.date(2024, 1, 1), TODAY).startswith(handler.ARCHIVE_URL)
    assert "timezone=UTC" in handler.build_url(dt.date(2026, 10, 30), TODAY)


def test_to_rows_has_24_hours_per_city(payload):
    rows = handler.to_rows(payload, ingested_at=dt.datetime(2026, 11, 1, 6))
    assert len(rows) == 24 * len(handler.CITIES)
    assert {r[0] for r in rows} == {c for c, _, _ in handler.CITIES}
    assert all(len(r) == len(handler.COLUMNS) for r in rows)


def test_to_rows_rejects_missing_locations(payload):
    with pytest.raises(ValueError):
        handler.to_rows(payload[:2], ingested_at=dt.datetime(2026, 11, 1))


def test_write_parquet_keeps_schema(payload, tmp_path):
    path = tmp_path / "w.parquet"
    handler.write_parquet(handler.to_rows(payload, dt.datetime(2026, 11, 1)), path)
    schema = duckdb.sql(f"DESCRIBE SELECT * FROM '{path.as_posix()}'").fetchall()
    assert [(c[0], c[1]) for c in schema] == list(handler.COLUMNS.items())


def test_object_key_is_hive_partitioned():
    assert handler.object_key("/raw/weather/", dt.date(2026, 10, 30)) == "raw/weather/dt=2026-10-30/weather.parquet"


@mock_aws
def test_lambda_handler_writes_to_s3_idempotently(payload, monkeypatch):
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-south-2")
    monkeypatch.setenv("RAW_BUCKET", "lake")
    monkeypatch.setattr(handler, "fetch", lambda url: payload)
    s3 = boto3.client("s3")
    s3.create_bucket(Bucket="lake", CreateBucketConfiguration={"LocationConstraint": "eu-south-2"})

    first = handler.lambda_handler({"date": "2026-10-30"})
    handler.lambda_handler({"date": "2026-10-30"})

    keys = [o["Key"] for o in s3.list_objects_v2(Bucket="lake")["Contents"]]
    assert keys == ["raw/weather/dt=2026-10-30/weather.parquet"]
    assert first["rows"] == 144


def test_to_rows_rejects_days_without_data(payload):
    payload[0]["hourly"]["temperature_2m"][5] = None
    with pytest.raises(ValueError, match="madrid"):
        handler.to_rows(payload, ingested_at=dt.datetime(2026, 11, 1))
