"""Great Expectations validation of the raw IGDB bronze pull."""

from dagster import AssetCheckExecutionContext, AssetCheckResult, AssetKey, asset_check

from config.settings import load_settings
from quality.pipeline import run_quality_checks


@asset_check(asset=AssetKey(["bronze", "raw_games"]), name="ge_bronze_expectations")
def ge_bronze_expectations(context: AssetCheckExecutionContext) -> AssetCheckResult:
    """Validates the newest bronze batch against the Great Expectations suite.

    Non-blocking: a failure is surfaced here and logged, but dbt/embeddings
    still run — bronze data quality issues are visibility, not a hard gate,
    for a project this size.
    """
    settings = load_settings()
    result = run_quality_checks(settings)
    context.log.info(f"Quality check: {result.games_validated} games, success={result.success}")
    return AssetCheckResult(
        passed=result.success,
        metadata={
            "games_validated": result.games_validated,
            "failed_expectations": result.failed_expectations,
        },
    )
