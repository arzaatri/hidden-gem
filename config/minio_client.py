"""Shared boto3 S3 client factory for talking to MinIO."""

from __future__ import annotations

import boto3

from config.settings import MinioConfig, Secrets


def s3_client(minio: MinioConfig, secrets: Secrets):
    scheme = "https" if minio.use_ssl else "http"
    return boto3.client(
        "s3",
        endpoint_url=f"{scheme}://{minio.endpoint}",
        aws_access_key_id=secrets.minio_root_user,
        aws_secret_access_key=secrets.minio_root_password,
    )
