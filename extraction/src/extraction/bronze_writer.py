"""Writes raw IGDB game records to the bronze layer in MinIO as NDJSON."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import boto3

from config.settings import MinioConfig, Secrets


def _s3_client(minio: MinioConfig, secrets: Secrets):
    scheme = "https" if minio.use_ssl else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{minio.endpoint}",
        aws_access_key_id=secrets.minio_root_user,
        aws_secret_access_key=secrets.minio_root_password,
    )


def ensure_bucket_exists(minio: MinioConfig, secrets: Secrets) -> None:
    client = _s3_client(minio, secrets)
    existing = {b["Name"] for b in client.list_buckets().get("Buckets", [])}
    if minio.bucket not in existing:
        client.create_bucket(Bucket=minio.bucket)


def write_bronze(records: list[dict[str, Any]], minio: MinioConfig, secrets: Secrets) -> str:
    """Writes one NDJSON file (one line per game) to bronze/ and returns its object key."""
    ensure_bucket_exists(minio, secrets)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    key = f"{minio.bronze_prefix}/games_{timestamp}.json"
    body = "\n".join(json.dumps(record) for record in records)

    client = _s3_client(minio, secrets)
    client.put_object(Bucket=minio.bucket, Key=key, Body=body.encode("utf-8"))
    return key
