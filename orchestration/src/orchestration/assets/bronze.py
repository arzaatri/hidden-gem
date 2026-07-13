"""The single Python (non-dbt) asset in the pipeline: pulls IGDB games into bronze."""

from dagster import AssetExecutionContext, MaterializeResult, asset

from config.settings import load_settings
from extraction.pipeline import run_extraction


@asset(key_prefix=["bronze"], name="raw_games")
def raw_games(context: AssetExecutionContext) -> MaterializeResult:
    """Incrementally pulls IGDB games updated since the last sync into MinIO bronze/."""
    settings = load_settings()
    result = run_extraction(settings)
    context.log.info(
        f"Pulled {result.games_pulled} games "
        f"(watermark {result.watermark_before} -> {result.watermark_after})"
    )
    return MaterializeResult(
        metadata={
            "games_pulled": result.games_pulled,
            "bronze_object_key": result.bronze_object_key or "(no new games)",
            "watermark_after": str(result.watermark_after),
        }
    )
