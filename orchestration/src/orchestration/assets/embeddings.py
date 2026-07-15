"""Precomputes CV/NLP embeddings for games, downstream of the dbt gold model."""

from dagster import AssetExecutionContext, AssetKey, MaterializeResult, asset

from config.settings import load_settings
from embeddings.pipeline import run_embeddings_pipeline


@asset(
    key_prefix=["embeddings"],
    name="game_embeddings",
    deps=[AssetKey(["gold", "dim_games"])],
)
def game_embeddings(context: AssetExecutionContext) -> MaterializeResult:
    """Embeds summary/storyline/cover art/screenshots for games missing or stale embeddings."""
    settings = load_settings()
    result = run_embeddings_pipeline(settings)
    context.log.info(f"Embedded {result.games_embedded} games")
    return MaterializeResult(metadata={"games_embedded": result.games_embedded})
