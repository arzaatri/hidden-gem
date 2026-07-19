"""Reads the silver screenshots table (MinIO parquet) for embedding input.

Screenshots only live in silver (per the medallion layering — gold doesn't
carry per-screenshot detail), so this reads MinIO directly rather than
querying Postgres.
"""

from __future__ import annotations

import io

import polars as pl

from config.minio_client import s3_client
from config.settings import MinioConfig, Secrets


def read_screenshot_urls(minio: MinioConfig, secrets: Secrets) -> dict[int, list[str]]:
    """Returns {game_id: [screenshot_url, ...]}."""
    client = s3_client(minio, secrets)
    key = f"{minio.silver_prefix}/screenshots.parquet"
    body = client.get_object(Bucket=minio.bucket, Key=key)["Body"].read()
    df = pl.read_parquet(io.BytesIO(body))

    urls_by_game: dict[int, list[str]] = {}
    for game_id, url in df.select("game_id", "url").iter_rows():
        # IGDB returns protocol-relative URLs ("//images.igdb.com/..."); add
        # a scheme so requests.get() can use them directly.
        full_url = f"https:{url}" if url.startswith("//") else url
        urls_by_game.setdefault(game_id, []).append(full_url)
    return urls_by_game
