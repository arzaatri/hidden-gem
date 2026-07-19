"""Reads the most recently written bronze batch (NDJSON in MinIO) for validation."""

from __future__ import annotations

import io

import pandas as pd

from config.minio_client import s3_client
from config.settings import MinioConfig, Secrets


def get_latest_bronze_batch(minio: MinioConfig, secrets: Secrets) -> pd.DataFrame | None:
    """Returns the newest bronze/*.json file as a DataFrame, or None if bronze is empty."""
    client = s3_client(minio, secrets)
    response = client.list_objects_v2(Bucket=minio.bucket, Prefix=f"{minio.bronze_prefix}/")
    objects = response.get("Contents", [])
    if not objects:
        return None

    latest_key = max(objects, key=lambda obj: obj["LastModified"])["Key"]
    body = client.get_object(Bucket=minio.bucket, Key=latest_key)["Body"].read()
    # convert_dates=False: pandas otherwise auto-detects columns like `updated_at`
    # by name and silently coerces them to datetime64, while similarly-shaped
    # epoch columns (e.g. `first_release_date`) are left as raw numbers — an
    # inconsistency that breaks numeric expectations on the epoch values.
    return pd.read_json(io.BytesIO(body), lines=True, convert_dates=False)
