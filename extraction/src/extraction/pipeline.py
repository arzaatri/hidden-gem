"""Ties auth -> IGDB fetch -> bronze write -> watermark upsert into one run."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import BaseModel

from config.settings import Settings
from extraction.bronze_writer import write_bronze
from extraction.igdb_auth import IgdbTokenProvider
from extraction.igdb_client import IgdbClient
from extraction.watermark import ensure_watermark_table, get_watermark, set_watermark

logger = logging.getLogger(__name__)


class ExtractionResult(BaseModel):
    games_pulled: int
    bronze_object_key: str | None
    watermark_before: datetime
    watermark_after: datetime


def run_extraction(settings: Settings) -> ExtractionResult:
    dsn = settings.postgres_dsn()
    ensure_watermark_table(dsn)
    watermark_before = get_watermark(dsn)
    logger.info("Starting extraction (updated_after=%s, max_games=%d)", watermark_before, settings.etl.max_games)

    token_provider = IgdbTokenProvider(settings.igdb, settings.secrets)
    client = IgdbClient(settings.igdb, token_provider)
    games = client.fetch_games(updated_after=watermark_before, max_games=settings.etl.max_games)

    if not games:
        logger.info("No games updated since %s", watermark_before)
        return ExtractionResult(
            games_pulled=0,
            bronze_object_key=None,
            watermark_before=watermark_before,
            watermark_after=watermark_before,
        )

    bronze_key = write_bronze(games, settings.minio, settings.secrets)
    logger.info("Wrote %d games to bronze/%s", len(games), bronze_key)

    watermark_after = max(
        datetime.fromtimestamp(game["updated_at"], tz=timezone.utc) for game in games
    )
    set_watermark(dsn, watermark_after)
    logger.info("Advanced watermark %s -> %s", watermark_before, watermark_after)

    return ExtractionResult(
        games_pulled=len(games),
        bronze_object_key=bronze_key,
        watermark_before=watermark_before,
        watermark_after=watermark_after,
    )
